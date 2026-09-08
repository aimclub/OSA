"""Run the paper -> graph pipeline over many PDFs: layout first, then VLM.

``python -m osa_tool.tools.paper_parsing.async_batch ./papers --batch-size 4 --output-dir out``

The run has two phases, and the order between them is a correctness requirement,
not a scheduling preference:

1. **Layout.** Every PDF is detected in turn and its elements written to
   ``<output-dir>/<stem>/layout.json`` with the rendered pages beside it. This is
   synchronous CPU work that holds the event loop for its whole duration.
2. **Describe.** Each saved layout is loaded back and its elements are described
   by the VLM, ``--batch-size`` papers at a time. Nothing blocks the loop here, so
   in-flight requests are actually serviced.

Running the two interleaved — a paper detecting layout while another paper's
requests were in flight — froze the loop for minutes at a time and stranded those
requests until they timed out, silently costing every paper a prefix of its text.
Going through disk also bounds memory to one paper's elements at a time and makes
the describe phase re-runnable without paying for detection again.

The ceiling on in-flight VLM requests is ``batch_size * max_concurrent``; raise
either one with the rate limits of the endpoint in mind.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import time
from argparse import Namespace
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import dotenv
from tqdm import tqdm

from osa_tool.config.settings import ConfigManager, ModelSettings
from osa_tool.operations.analysis.repository_validation.paper_parsing.layout_io import PAGES_DIRNAME, layout_exists
from osa_tool.operations.analysis.repository_validation.paper_parsing.models import PaperParsingOptions
from osa_tool.operations.analysis.repository_validation.paper_parsing.structured_parser import (
    DEFAULT_API_KEY_ENV,
    StructuredPaperParser,
)
from osa_tool.tools.paper_parsing.batch import build_options, collect_pdf_inputs
from osa_tool.utils.logger import logger


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass
class PaperOutcome:
    """What happened to a single PDF, as recorded in the run manifest."""

    pdf: str
    status: str
    output_dir: str
    stage: str = "layout"
    duration_seconds: float = 0.0
    elements: int | None = None
    requested: int | None = None
    described: int | None = None
    nodes: int | None = None
    edges: int | None = None
    error: str | None = None
    finished_at: str = field(default_factory=timestamp)

    @property
    def described_ratio(self) -> float | None:
        """Share of requested elements the VLM actually returned text for."""
        if not self.requested:
            return None
        return (self.described or 0) / self.requested


@dataclass
class RunSummary:
    """Aggregated result of a batched run, checkpointed as it goes.

    ``complete`` stays False until the run finishes, so a manifest left by a run
    that was killed — which on a memory-tight box is the likely way a long run
    ends — is recognizable as partial rather than silently looking like a finished
    run that processed fewer papers.
    """

    total: int = 0
    outcomes: list[PaperOutcome] = field(default_factory=list)
    started_at: str = field(default_factory=timestamp)
    complete: bool = False

    def upsert(self, outcome: PaperOutcome) -> None:
        """Record an outcome, replacing any earlier one for the same paper.

        A paper is reported once per phase; the describe phase supersedes what the
        layout phase recorded rather than adding a second row for it.
        """
        for position, existing in enumerate(self.outcomes):
            if existing.pdf == outcome.pdf:
                self.outcomes[position] = outcome
                return
        self.outcomes.append(outcome)

    def by_status(self, status: str) -> list[PaperOutcome]:
        return [outcome for outcome in self.outcomes if outcome.status == status]

    @property
    def failed(self) -> list[PaperOutcome]:
        return self.by_status("failed")


def read_list_file(path: Path) -> list[Path]:
    """Read a newline-separated list of PDF paths; ``#`` comments and blanks are skipped."""
    lines = path.expanduser().read_text(encoding="utf-8").splitlines()
    return [Path(line.strip()) for line in lines if line.strip() and not line.lstrip().startswith("#")]


def chunked(items: list, size: int) -> list[list]:
    return [items[start : start + size] for start in range(0, len(items), size)]


def assign_output_dirs(pdfs: list[Path], output_dir: Path) -> dict[Path, Path]:
    """Give every PDF its own output directory, disambiguating repeated file stems."""
    seen: dict[str, int] = {}
    destinations: dict[Path, Path] = {}
    for pdf in pdfs:
        count = seen.get(pdf.stem, 0)
        seen[pdf.stem] = count + 1
        destinations[pdf] = output_dir / (pdf.stem if count == 0 else f"{pdf.stem}_{count + 1}")
    return destinations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a list of PDF papers into markdown and document graphs: layout first, then VLM."
    )
    parser.add_argument("pdfs", nargs="*", type=Path, help="PDF files or directories of PDFs.")
    parser.add_argument(
        "--from-file",
        type=Path,
        default=None,
        help="File holding one PDF path (or directory) per line; combined with any positional paths.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("paper_parsing_results"))
    parser.add_argument("--batch-size", type=int, default=4, help="Papers described concurrently per batch.")
    parser.add_argument(
        "--phase",
        choices=["all", "layout", "describe"],
        default="all",
        help="Run only layout detection, only description of an existing layout, or both (default).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip work already on disk: layout.json for the layout phase, document.md for the describe phase.",
    )
    parser.add_argument(
        "--cleanup-pages",
        action="store_true",
        help="Delete the rendered pages once a paper is described. Saves disk, but a later "
        "--phase describe then has no full-page context images to send.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Where to write the run manifest (default: <output-dir>/manifest.json).",
    )
    parser.add_argument("--config-file", default=None)
    parser.add_argument("--model", default=None, help="Vision-language model; overrides the configured vlm_model.")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible endpoint serving the VLM.")
    parser.add_argument(
        "--api-key-env",
        default=None,
        help=f"Environment variable holding the API key (default: configuration, else {DEFAULT_API_KEY_ENV}).",
    )
    parser.add_argument("--device", default=None, choices=["cpu", "cuda"])
    parser.add_argument("--conf-threshold", type=float, default=None)
    parser.add_argument("--max-concurrent", type=int, default=None, help="Concurrent VLM requests per paper.")
    parser.add_argument("--downsample-factor", type=int, default=None)
    parser.add_argument(
        "--render-dpi",
        type=int,
        default=None,
        help="Page rasterization DPI (default 200). Lowering it cuts memory roughly quadratically.",
    )
    parser.add_argument("--layout-batch-size", type=int, default=None, help="Pages per layout-detection call.")
    parser.add_argument("--vlm-max-retries", type=int, default=None, help="Retries per element (default 3).")
    parser.add_argument("--vlm-retry-delay", type=float, default=None, help="Backoff base in seconds (default 2).")
    parser.add_argument("--vlm-timeout", type=float, default=None, help="Per-request timeout in seconds.")
    parser.add_argument("--save-img", action="store_true", help="Keep the rendered element crops on disk.")
    parser.add_argument("--include-report", action="store_true", help="Also export the raw layout report.")
    return parser


def make_parser(
    pdf: Path,
    args: Namespace,
    model_settings: ModelSettings,
    options: PaperParsingOptions,
) -> StructuredPaperParser:
    return StructuredPaperParser.from_model_settings(
        pdf,
        model_settings,
        vlm_model=args.model,
        vlm_base_url=args.base_url,
        api_key=os.getenv(args.api_key_env) if args.api_key_env else None,
        options=options,
    )


def layout_paper(
    pdf: Path,
    destination: Path,
    args: Namespace,
    model_settings: ModelSettings,
    options: PaperParsingOptions,
) -> PaperOutcome:
    """Phase 1 for one paper: detect layout and persist it. Never raises."""
    if args.skip_existing and layout_exists(destination):
        logger.info("Skipping layout for %s: %s already exists", pdf, destination / "layout.json")
        return PaperOutcome(pdf=str(pdf), status="skipped", output_dir=str(destination), stage="layout")

    started = time.perf_counter()
    try:
        elements = make_parser(pdf, args, model_settings, options).parse_layout(destination)
    except Exception as exc:
        logger.error("Layout detection failed for %s: %s", pdf, exc, exc_info=True)
        return PaperOutcome(
            pdf=str(pdf),
            status="failed",
            output_dir=str(destination),
            stage="layout",
            duration_seconds=round(time.perf_counter() - started, 2),
            error=f"{type(exc).__name__}: {exc}",
        )
    return PaperOutcome(
        pdf=str(pdf),
        status="ok",
        output_dir=str(destination),
        stage="layout",
        duration_seconds=round(time.perf_counter() - started, 2),
        elements=elements,
    )


async def describe_paper(
    pdf: Path,
    destination: Path,
    args: Namespace,
    model_settings: ModelSettings,
    options: PaperParsingOptions,
) -> PaperOutcome:
    """Phase 2 for one paper: describe the saved layout and export. Never raises."""
    if args.skip_existing and (destination / "document.md").exists():
        logger.info("Skipping description for %s: %s already exists", pdf, destination / "document.md")
        return PaperOutcome(pdf=str(pdf), status="skipped", output_dir=str(destination), stage="describe")

    started = time.perf_counter()
    try:
        parser = make_parser(pdf, args, model_settings, options)
        result = await parser.adescribe(destination)
        # export() renders files, so keep the blocking IO off the event loop.
        await asyncio.to_thread(parser.export, result, destination, include_report=args.include_report)
        if args.cleanup_pages:
            await asyncio.to_thread(shutil.rmtree, destination / PAGES_DIRNAME, True)
    except Exception as exc:
        logger.error("Description failed for %s: %s", pdf, exc, exc_info=True)
        return PaperOutcome(
            pdf=str(pdf),
            status="failed",
            output_dir=str(destination),
            stage="describe",
            duration_seconds=round(time.perf_counter() - started, 2),
            error=f"{type(exc).__name__}: {exc}",
        )

    meta = result.graph.get("meta", {})
    return PaperOutcome(
        pdf=str(pdf),
        status="ok",
        output_dir=str(destination),
        stage="describe",
        duration_seconds=round(time.perf_counter() - started, 2),
        elements=len(result.report),
        requested=result.requested,
        described=result.described,
        nodes=meta.get("total_nodes"),
        edges=meta.get("total_edges"),
    )


async def guarded(
    pdf: Path,
    destination: Path,
    args: Namespace,
    model_settings: ModelSettings,
    options: PaperParsingOptions,
) -> PaperOutcome:
    """:func:`describe_paper` that always yields an outcome, never an exception.

    ``describe_paper`` already reports its own failures as outcomes; this catches
    the driver itself breaking, so completions can be consumed in the order they
    land without having to map an exception back to the paper that caused it.
    """
    try:
        return await describe_paper(pdf, destination, args, model_settings, options)
    except Exception as exc:
        logger.error("Describe task for %s crashed: %s", pdf, exc, exc_info=True)
        return PaperOutcome(
            pdf=str(pdf),
            status="failed",
            output_dir=str(destination),
            stage="describe",
            error=f"{type(exc).__name__}: {exc}",
        )


def run_layout_phase(
    pdfs: list[Path],
    destinations: dict[Path, Path],
    args: Namespace,
    model_settings: ModelSettings,
    options: PaperParsingOptions,
    summary: RunSummary,
    manifest_path: Path | None,
) -> list[Path]:
    """Detect and persist the layout of every paper; return those that succeeded.

    Sequential on purpose. This is the memory-hungry stage, and running papers in
    parallel here is what the on-disk handoff exists to avoid.
    """
    logger.info("Phase 1/2: detecting layout for %s paper(s)", len(pdfs))
    ready: list[Path] = []
    with tqdm(total=len(pdfs), desc="layout", unit="paper") as progress:
        for pdf in pdfs:
            outcome = layout_paper(pdf, destinations[pdf], args, model_settings, options)
            summary.upsert(outcome)
            if outcome.status != "failed":
                ready.append(pdf)
            progress.update(1)
            progress.set_postfix(ok=len(summary.by_status("ok")), failed=len(summary.failed), refresh=False)
            if manifest_path is not None:
                write_manifest(summary, manifest_path)
    logger.info("Phase 1/2 completed: %s of %s paper(s) have a layout", len(ready), len(pdfs))
    return ready


async def run_describe_phase(
    pdfs: list[Path],
    destinations: dict[Path, Path],
    args: Namespace,
    model_settings: ModelSettings,
    options: PaperParsingOptions,
    summary: RunSummary,
    manifest_path: Path | None,
) -> None:
    """Describe the saved layouts, ``batch_size`` papers at a time."""
    batches = chunked(pdfs, args.batch_size)
    logger.info(
        "Phase 2/2: describing %s paper(s) in %s batch(es) of up to %s, %s VLM request(s) per paper",
        len(pdfs),
        len(batches),
        args.batch_size,
        options.max_concurrent,
    )
    with tqdm(total=len(pdfs), desc="describing", unit="paper") as progress:
        for number, batch in enumerate(batches, start=1):
            logger.info("Batch %s/%s: %s", number, len(batches), ", ".join(pdf.name for pdf in batch))
            started = time.perf_counter()
            tasks = [
                asyncio.ensure_future(guarded(pdf, destinations[pdf], args, model_settings, options)) for pdf in batch
            ]
            for completion in asyncio.as_completed(tasks):
                outcome = await completion
                summary.upsert(outcome)
                progress.update(1)
                progress.set_postfix(
                    ok=len(summary.by_status("ok")),
                    skipped=len(summary.by_status("skipped")),
                    failed=len(summary.failed),
                    refresh=False,
                )
                if manifest_path is not None:
                    write_manifest(summary, manifest_path)
            logger.info("Batch %s/%s finished in %.2fs", number, len(batches), time.perf_counter() - started)


async def run_batches(
    pdfs: list[Path],
    args: Namespace,
    model_settings: ModelSettings,
    options: PaperParsingOptions,
    manifest_path: Path | None = None,
) -> RunSummary:
    """Run the requested phases over every PDF.

    The manifest is checkpointed on every paper in both phases, so a run that is
    interrupted still leaves an accurate record of what was done.
    """
    destinations = assign_output_dirs(pdfs, args.output_dir)
    summary = RunSummary(total=len(pdfs))
    phase = getattr(args, "phase", "all")

    if phase in ("all", "layout"):
        ready = run_layout_phase(pdfs, destinations, args, model_settings, options, summary, manifest_path)
    else:
        # Describing on its own: take whatever the earlier layout phase left behind.
        ready = [pdf for pdf in pdfs if layout_exists(destinations[pdf])]
        missing = len(pdfs) - len(ready)
        if missing:
            logger.warning("%s paper(s) have no layout.json and will be skipped; run --phase layout first", missing)
            for pdf in pdfs:
                if not layout_exists(destinations[pdf]):
                    summary.upsert(
                        PaperOutcome(
                            pdf=str(pdf),
                            status="failed",
                            output_dir=str(destinations[pdf]),
                            stage="describe",
                            error="No layout.json; run --phase layout first",
                        )
                    )

    if phase in ("all", "describe") and ready:
        await run_describe_phase(ready, destinations, args, model_settings, options, summary, manifest_path)

    summary.complete = True
    if manifest_path is not None:
        # The checkpoints written inside the phases all say complete=False, so the
        # run has to stamp its own completion — otherwise a finished run leaves a
        # manifest indistinguishable from one that was interrupted.
        write_manifest(summary, manifest_path)
    return summary


def write_manifest(summary: RunSummary, path: Path, *, log: bool = False) -> None:
    """Write the run manifest, replacing any previous one atomically.

    This is called after every paper, so a partial write interrupted by a kill
    would otherwise leave unparseable JSON where the record of the run should be;
    writing beside the target and renaming means the manifest is always either the
    previous checkpoint or the current one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    requested = sum(outcome.requested or 0 for outcome in summary.outcomes)
    described = sum(outcome.described or 0 for outcome in summary.outcomes)
    payload = {
        "started_at": summary.started_at,
        "updated_at": timestamp(),
        "complete": summary.complete,
        "requested": summary.total,
        "total": len(summary.outcomes),
        "ok": len(summary.by_status("ok")),
        "skipped": len(summary.by_status("skipped")),
        "failed": len(summary.failed),
        # Elements the VLM was asked about vs. elements it answered for. A run can
        # report every paper "ok" while most of its text is missing, so the ratio
        # belongs in the manifest rather than only in the logs.
        "elements_requested": requested,
        "elements_described": described,
        "described_ratio": round(described / requested, 4) if requested else None,
        "papers": [asdict(outcome) for outcome in summary.outcomes],
    }
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
    if log:
        logger.info("Manifest written to %s", path)


def main() -> int:
    args = build_parser().parse_args()

    requested = list(args.pdfs)
    if args.from_file:
        requested.extend(read_list_file(args.from_file))
    if not requested:
        print("ERROR: no input given; pass PDF paths, a directory, or --from-file")
        return 1
    if args.batch_size < 1:
        print("ERROR: --batch-size must be at least 1")
        return 1

    pdfs, input_failures = collect_pdf_inputs(requested)
    for failure in input_failures:
        print(f"ERROR: {failure}")
    if not pdfs:
        return 1

    dotenv.load_dotenv()
    config = ConfigManager(Namespace(config_file=args.config_file) if args.config_file else None)
    model_settings = config.get_model_settings("validation")
    options = build_options(args, model_settings)

    manifest_path = args.manifest or args.output_dir / "manifest.json"
    summary = asyncio.run(run_batches(pdfs, args, model_settings, options, manifest_path=manifest_path))
    write_manifest(summary, manifest_path, log=True)

    for outcome in summary.outcomes:
        ratio = outcome.described_ratio
        detail = f" ({outcome.error})" if outcome.error else (f" described {ratio:.0%}" if ratio is not None else "")
        print(f"{outcome.status.upper()}: {outcome.pdf}{detail}")
    print(
        f"Done: {len(summary.by_status('ok'))} ok, "
        f"{len(summary.by_status('skipped'))} skipped, {len(summary.failed)} failed"
    )

    return 1 if summary.failed or input_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
