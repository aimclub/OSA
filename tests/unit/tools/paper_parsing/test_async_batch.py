import pytest

pytest.importorskip("doclayout_yolo", reason="paper_parsing optional dependency group is not installed")

import asyncio
import json
from argparse import Namespace
from pathlib import Path

from osa_tool.operations.analysis.repository_validation.paper_parsing.models import PaperParsingOptions
from osa_tool.tools.paper_parsing import async_batch
from osa_tool.tools.paper_parsing.async_batch import (
    PaperOutcome,
    RunSummary,
    assign_output_dirs,
    build_parser,
    chunked,
    describe_paper,
    read_list_file,
    run_batches,
    write_manifest,
)
from tests.unit.operations.analysis.repository_validation.paper_parsing.fixtures import make_settings


def run_args(output_dir: Path, **overrides) -> Namespace:
    defaults = {
        "output_dir": output_dir,
        "batch_size": 2,
        "phase": "all",
        "skip_existing": False,
        "cleanup_pages": False,
        "model": None,
        "base_url": None,
        "api_key_env": None,
        "include_report": False,
    }
    return Namespace(**{**defaults, **overrides})


def make_pdfs(tmp_path: Path, count: int) -> list[Path]:
    pdfs = []
    for index in range(count):
        pdf = tmp_path / f"paper_{index}.pdf"
        pdf.write_bytes(b"%PDF-test")
        pdfs.append(pdf)
    return pdfs


class FakeParser:
    """Stand-in for StructuredPaperParser recording phase order and concurrency."""

    events: list[str] = []
    in_flight = 0
    peak_in_flight = 0
    exported: list[str] = []
    fail_layout: set[str] = set()
    fail_describe: set[str] = set()

    def __init__(self, pdf_path, *_, **__):
        self.path = Path(pdf_path)

    @classmethod
    def reset(cls):
        cls.events = []
        cls.in_flight = 0
        cls.peak_in_flight = 0
        cls.exported = []
        cls.fail_layout = set()
        cls.fail_describe = set()

    @classmethod
    def from_model_settings(cls, pdf_path, model_settings, **kwargs):
        return cls(pdf_path)

    def parse_layout(self, destination):
        if self.path.name in FakeParser.fail_layout:
            raise RuntimeError("layout boom")
        FakeParser.events.append(f"layout:{self.path.stem}")
        Path(destination).mkdir(parents=True, exist_ok=True)
        (Path(destination) / "layout.json").write_text('{"version": 1, "elements": []}')
        (Path(destination) / "pages").mkdir(exist_ok=True)
        return 7

    async def adescribe(self, destination):
        if self.path.name in FakeParser.fail_describe:
            raise RuntimeError("describe boom")
        FakeParser.events.append(f"describe:{self.path.stem}")
        FakeParser.in_flight += 1
        FakeParser.peak_in_flight = max(FakeParser.peak_in_flight, FakeParser.in_flight)
        try:
            await asyncio.sleep(0.01)
        finally:
            FakeParser.in_flight -= 1
        return Namespace(
            graph={"meta": {"total_nodes": 3, "total_edges": 2}},
            report=[{}] * 7,
            requested=7,
            described=6,
        )

    @staticmethod
    def export(result, output_dir, *, include_report=False):
        FakeParser.exported.append(Path(output_dir).name)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        (Path(output_dir) / "document.md").write_text("body")


@pytest.fixture
def fake_parser(monkeypatch):
    FakeParser.reset()
    monkeypatch.setattr(async_batch, "StructuredPaperParser", FakeParser)
    return FakeParser


def statuses(summary) -> dict:
    """Outcomes keyed by paper name; completions arrive in finishing order."""
    return {Path(outcome.pdf).name: outcome for outcome in summary.outcomes}


def test_chunked_splits_into_fixed_size_batches():
    assert chunked([Path(str(i)) for i in range(5)], 2) == [
        [Path("0"), Path("1")],
        [Path("2"), Path("3")],
        [Path("4")],
    ]


def test_read_list_file_ignores_blanks_and_comments(tmp_path):
    listing = tmp_path / "papers.txt"
    listing.write_text("a.pdf\n\n# skip me\n  b.pdf  \n")

    assert read_list_file(listing) == [Path("a.pdf"), Path("b.pdf")]


def test_repeated_stems_get_distinct_output_dirs(tmp_path):
    pdfs = [Path("/one/paper.pdf"), Path("/two/paper.pdf")]

    destinations = assign_output_dirs(pdfs, tmp_path)

    assert destinations[pdfs[0]] == tmp_path / "paper"
    assert destinations[pdfs[1]] == tmp_path / "paper_2"


def test_batch_defaults_to_running_both_phases():
    args = build_parser().parse_args(["paper.pdf"])

    assert args.batch_size == 4
    assert args.phase == "all"
    assert args.from_file is None


def test_every_layout_finishes_before_any_description_starts(tmp_path, fake_parser):
    """The ordering is the fix: layout freezes the loop, so it must not overlap VLM work."""
    pdfs = make_pdfs(tmp_path, 4)

    asyncio.run(run_batches(pdfs, run_args(tmp_path / "out", batch_size=2), make_settings(), PaperParsingOptions()))

    kinds = [event.split(":")[0] for event in fake_parser.events]
    assert kinds == ["layout"] * 4 + ["describe"] * 4


def test_papers_are_described_concurrently_within_a_batch(tmp_path, fake_parser):
    pdfs = make_pdfs(tmp_path, 4)

    summary = asyncio.run(
        run_batches(pdfs, run_args(tmp_path / "out", batch_size=2), make_settings(), PaperParsingOptions())
    )

    assert [outcome.status for outcome in summary.outcomes] == ["ok"] * 4
    assert fake_parser.peak_in_flight == 2
    assert summary.outcomes[0].nodes == 3
    assert summary.complete is True


def test_each_paper_is_reported_once_across_both_phases(tmp_path, fake_parser):
    pdfs = make_pdfs(tmp_path, 3)

    summary = asyncio.run(run_batches(pdfs, run_args(tmp_path / "out"), make_settings(), PaperParsingOptions()))

    assert len(summary.outcomes) == 3
    assert {outcome.stage for outcome in summary.outcomes} == {"describe"}


def test_a_paper_whose_layout_fails_is_never_described(tmp_path, fake_parser):
    pdfs = make_pdfs(tmp_path, 3)
    fake_parser.fail_layout = {"paper_1.pdf"}

    summary = asyncio.run(run_batches(pdfs, run_args(tmp_path / "out"), make_settings(), PaperParsingOptions()))

    by_name = statuses(summary)
    assert by_name["paper_1.pdf"].status == "failed"
    assert by_name["paper_1.pdf"].stage == "layout"
    assert "describe:paper_1" not in fake_parser.events
    assert by_name["paper_0.pdf"].status == "ok"


def test_a_failing_description_does_not_abort_the_batch(tmp_path, fake_parser):
    pdfs = make_pdfs(tmp_path, 3)
    fake_parser.fail_describe = {"paper_1.pdf"}

    summary = asyncio.run(
        run_batches(pdfs, run_args(tmp_path / "out", batch_size=3), make_settings(), PaperParsingOptions())
    )

    by_name = statuses(summary)
    assert [by_name[f"paper_{i}.pdf"].status for i in range(3)] == ["ok", "failed", "ok"]
    assert "RuntimeError: describe boom" in summary.failed[0].error


def test_layout_only_phase_stops_before_the_vlm(tmp_path, fake_parser):
    pdfs = make_pdfs(tmp_path, 2)

    summary = asyncio.run(
        run_batches(pdfs, run_args(tmp_path / "out", phase="layout"), make_settings(), PaperParsingOptions())
    )

    assert [event.split(":")[0] for event in fake_parser.events] == ["layout", "layout"]
    assert {outcome.stage for outcome in summary.outcomes} == {"layout"}
    assert summary.outcomes[0].elements == 7


def test_describe_only_phase_uses_the_layout_already_on_disk(tmp_path, fake_parser):
    pdfs = make_pdfs(tmp_path, 2)
    out = tmp_path / "out"
    asyncio.run(run_batches(pdfs, run_args(out, phase="layout"), make_settings(), PaperParsingOptions()))
    fake_parser.events.clear()

    summary = asyncio.run(run_batches(pdfs, run_args(out, phase="describe"), make_settings(), PaperParsingOptions()))

    assert [event.split(":")[0] for event in fake_parser.events] == ["describe", "describe"]
    assert [outcome.status for outcome in summary.outcomes] == ["ok", "ok"]


def test_describe_only_phase_reports_papers_with_no_layout(tmp_path, fake_parser):
    pdfs = make_pdfs(tmp_path, 2)

    summary = asyncio.run(
        run_batches(pdfs, run_args(tmp_path / "out", phase="describe"), make_settings(), PaperParsingOptions())
    )

    assert [outcome.status for outcome in summary.outcomes] == ["failed", "failed"]
    assert "run --phase layout first" in summary.failed[0].error
    assert fake_parser.events == []


def test_skip_existing_skips_both_phases_independently(tmp_path, fake_parser):
    pdfs = make_pdfs(tmp_path, 2)
    out = tmp_path / "out"
    (out / "paper_0").mkdir(parents=True)
    (out / "paper_0" / "layout.json").write_text("{}")
    (out / "paper_0" / "document.md").write_text("already done")

    summary = asyncio.run(run_batches(pdfs, run_args(out, skip_existing=True), make_settings(), PaperParsingOptions()))

    by_name = statuses(summary)
    assert by_name["paper_0.pdf"].status == "skipped"
    assert by_name["paper_1.pdf"].status == "ok"
    assert fake_parser.exported == ["paper_1"]


def test_cleanup_pages_removes_the_rendered_pages(tmp_path, fake_parser):
    pdfs = make_pdfs(tmp_path, 1)
    out = tmp_path / "out"

    asyncio.run(run_batches(pdfs, run_args(out, cleanup_pages=True), make_settings(), PaperParsingOptions()))

    assert (out / "paper_0" / "layout.json").exists()
    assert not (out / "paper_0" / "pages").exists()


def test_pages_are_kept_by_default(tmp_path, fake_parser):
    pdfs = make_pdfs(tmp_path, 1)
    out = tmp_path / "out"

    asyncio.run(run_batches(pdfs, run_args(out), make_settings(), PaperParsingOptions()))

    assert (out / "paper_0" / "pages").exists()


def test_describe_paper_reports_the_failure_instead_of_raising(tmp_path, fake_parser):
    pdf = tmp_path / "paper_0.pdf"
    pdf.write_bytes(b"%PDF-test")
    fake_parser.fail_describe = {"paper_0.pdf"}

    outcome = asyncio.run(
        describe_paper(
            pdf, tmp_path / "out" / "paper_0", run_args(tmp_path / "out"), make_settings(), PaperParsingOptions()
        )
    )

    assert outcome.status == "failed"
    assert outcome.error.startswith("RuntimeError")


def test_manifest_carries_the_described_ratio(tmp_path, fake_parser):
    pdfs = make_pdfs(tmp_path, 2)
    manifest_path = tmp_path / "out" / "manifest.json"

    asyncio.run(
        run_batches(
            pdfs,
            run_args(tmp_path / "out"),
            make_settings(),
            PaperParsingOptions(),
            manifest_path=manifest_path,
        )
    )

    manifest = json.loads(manifest_path.read_text())
    assert manifest["elements_requested"] == 14
    assert manifest["elements_described"] == 12
    assert manifest["described_ratio"] == pytest.approx(12 / 14, rel=1e-3)


def test_the_manifest_is_checkpointed_after_every_paper(tmp_path, fake_parser):
    """A run killed midway must still leave a record of what finished."""
    pdfs = make_pdfs(tmp_path, 3)
    manifest_path = tmp_path / "out" / "manifest.json"
    seen = []

    original_export = FakeParser.export

    def export_then_snapshot(result, output_dir, *, include_report=False):
        original_export(result, output_dir, include_report=include_report)
        seen.append(json.loads(manifest_path.read_text())["ok"])

    fake_parser.export = staticmethod(export_then_snapshot)
    try:
        asyncio.run(
            run_batches(
                pdfs,
                run_args(tmp_path / "out", batch_size=1),
                make_settings(),
                PaperParsingOptions(),
                manifest_path=manifest_path,
            )
        )
    finally:
        fake_parser.export = staticmethod(original_export)

    # The manifest was already on disk and growing before the run ended.
    assert seen == [3, 3, 3]
    assert json.loads(manifest_path.read_text())["complete"] is True


def test_a_checkpoint_is_marked_incomplete_until_the_run_ends(tmp_path):
    summary = RunSummary(total=3)
    summary.upsert(PaperOutcome(pdf="a.pdf", status="ok", output_dir="out/a"))
    path = tmp_path / "manifest.json"

    write_manifest(summary, path)
    checkpoint = json.loads(path.read_text())

    summary.complete = True
    write_manifest(summary, path)
    final = json.loads(path.read_text())

    assert checkpoint["complete"] is False
    assert checkpoint["requested"] == 3 and checkpoint["total"] == 1
    assert final["complete"] is True


def test_the_manifest_is_replaced_atomically(tmp_path):
    summary = RunSummary(total=1)
    summary.upsert(PaperOutcome(pdf="a.pdf", status="ok", output_dir="out/a"))
    path = tmp_path / "manifest.json"

    write_manifest(summary, path)
    write_manifest(summary, path)

    assert json.loads(path.read_text())["total"] == 1
    assert not (tmp_path / "manifest.json.tmp").exists()


def test_upsert_replaces_the_earlier_phase_entry():
    summary = RunSummary(total=1)
    summary.upsert(PaperOutcome(pdf="a.pdf", status="ok", output_dir="out/a", stage="layout"))
    summary.upsert(PaperOutcome(pdf="a.pdf", status="ok", output_dir="out/a", stage="describe"))

    assert len(summary.outcomes) == 1
    assert summary.outcomes[0].stage == "describe"
