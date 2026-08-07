from __future__ import annotations

import asyncio
import json
from pathlib import Path

from osa_tool.operations.analysis.repository_validation.paper_parsing.doc_graph import build_document_graph
from osa_tool.operations.analysis.repository_validation.paper_parsing.doc_layout import LayoutExtractor
from osa_tool.operations.analysis.repository_validation.paper_parsing.doc_ocr import ImageDescription
from osa_tool.operations.analysis.repository_validation.paper_parsing.exceptions import (
    DescriptionError,
    LayoutDetectionError,
)
from osa_tool.operations.analysis.repository_validation.paper_parsing.graph_utils import save_graph
from osa_tool.operations.analysis.repository_validation.paper_parsing.models import (
    PaperParsingOptions,
    PaperParsingResult,
)
from osa_tool.utils.logger import logger


class PaperParsingPipeline:
    """Layout-aware, VLM-based PDF parsing pipeline.

    Runs the three ``paper_parsing`` stages — layout detection, per-element VLM
    description and document-graph construction — and linearizes the resulting
    graph into a single markdown-ish string. The VLM connection is configured
    on the pipeline; per-run tunables live in :class:`PaperParsingOptions`.
    """

    def __init__(
        self,
        *,
        vlm_model: str,
        vlm_base_url: str | None = None,
        api_key: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self.vlm_model = vlm_model
        self.vlm_base_url = vlm_base_url
        self.api_key = api_key
        self.system_prompt = system_prompt or "You are a technical document specialist."

    async def arun(self, pdf_path: Path | str, options: PaperParsingOptions | None = None) -> PaperParsingResult:
        options = options or PaperParsingOptions()
        pdf_path = Path(pdf_path)
        logger.info("Paper parsing pipeline started for %s", pdf_path)

        logger.info("Stage 1/3: running layout detection")
        extractor = LayoutExtractor(device=options.device, save_img=options.save_img)
        report = extractor.get_bboxes(str(pdf_path), conf_threshold=options.conf_threshold)
        if not report:
            raise LayoutDetectionError(f"Layout detection produced no elements for {pdf_path}")
        pages = extractor.pages
        logger.info("Stage 1/3 completed: detected %s layout elements", len(report))

        logger.info("Stage 2/3: describing layout elements with VLM %s", self.vlm_model)
        describer = ImageDescription(
            use_async=True,
            pages=pages,
            bbox_json=report,
            model_name=self.vlm_model,
            base_url=self.vlm_base_url,
            api_key=self.api_key,
            device=options.device,
        )
        results = await describer.process_all_bboxes_async(
            sys_prompt=self.system_prompt,
            max_concurrent=options.max_concurrent,
            downsample_factor=options.downsample_factor,
        )
        described = self._merge_descriptions(report, results, describer)
        logger.info("Stage 2/3 completed: described %s of %s elements", described, len(results))

        logger.info("Stage 3/3: building document graph and linearizing")
        graph = build_document_graph(report)
        markdown = self.linearize(graph)
        logger.info(
            "Stage 3/3 completed: graph has %s nodes, %s edges",
            graph["meta"]["total_nodes"],
            graph["meta"]["total_edges"],
        )

        logger.info("Paper parsing pipeline completed for %s", pdf_path)
        return PaperParsingResult(source_path=pdf_path, markdown=markdown, report=report, graph=graph)

    def run(self, pdf_path: Path | str, options: PaperParsingOptions | None = None) -> PaperParsingResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(pdf_path, options))
        raise RuntimeError(
            "PaperParsingPipeline.run() cannot be used inside an active event loop; await arun() instead"
        )

    @staticmethod
    def _merge_descriptions(report: list, results: list, describer: ImageDescription) -> int:
        """Merge VLM ``description`` / ``text`` back into each layout element.

        Mutates ``report`` in place and returns the number of elements that were
        successfully described. Raises :class:`DescriptionError` if every request
        failed.
        """
        succeeded = 0
        for item in results:
            if not item.get("success"):
                logger.warning(
                    "VLM description failed for bbox_idx %s: %s",
                    item.get("bbox_idx"),
                    item.get("error"),
                )
                continue
            idx = item["bbox_idx"]
            parsed = describer.parse_json(item["result"])
            report[idx]["text"] = parsed.get("text", "")
            report[idx]["description"] = parsed.get("description", "")
            succeeded += 1
        if results and succeeded == 0:
            raise DescriptionError("Every VLM description request failed")
        return succeeded

    @staticmethod
    def linearize(graph: dict) -> str:
        """Render the document graph as a single markdown-ish string.

        The graph is the input, not a by-product: element nodes carry the
        ``reading_rank`` the graph builder computed, and ``caption_of`` edges say
        which caption belongs to which figure. Linearizing from those means the
        text handed to the claim-extraction prompt and the graph handed to any
        other consumer describe the same document — previously this recomputed
        the ordering from the raw report and the graph was built then discarded,
        so the two could disagree.

        Titles become headings, paragraphs are emitted as-is, and figures /
        tables / formulas are emitted with their VLM description (plus any
        caption text) so non-textual context survives.
        """
        elements = [node for node in graph.get("nodes", []) if node.get("node_type") == "element"]
        captions = PaperParsingPipeline._captions_by_target(graph)

        blocks: list[str] = []
        for node in sorted(elements, key=lambda n: n.get("reading_rank", 0)):
            if not node.get("is_content", True):
                continue
            name = node.get("name", "")
            text = (node.get("text") or "").strip()
            description = (node.get("description") or "").strip()

            if name == "title":
                if text:
                    blocks.append(f"## {text}")
            elif name == "plain text":
                if text:
                    blocks.append(text)
            elif name in ("figure", "table", "isolate_formula"):
                label = "Formula" if name == "isolate_formula" else name.capitalize()
                body = " ".join(part for part in (description or text, captions.get(node["node_id"], "")) if part)
                if body:
                    blocks.append(f"[{label}] {body}")
            else:  # footnotes and anything else carrying text
                body = text or description
                if body:
                    blocks.append(body)

        return "\n\n".join(blocks)

    @staticmethod
    def _captions_by_target(graph: dict) -> dict[str, str]:
        """Map a figure / table node id to the text of the captions pointing at it.

        Captions folded into their figure's crop carry no text of their own, so
        this is usually empty — but a caption that survived as its own element
        still belongs with the figure rather than adrift in the reading order.
        """
        by_id = {node["node_id"]: node for node in graph.get("nodes", [])}

        texts: dict[str, list[str]] = {}
        for edge in graph.get("edges", []):
            if edge.get("edge_type") != "caption_of":
                continue
            caption = by_id.get(edge["source"])
            if caption is None:
                continue
            body = (caption.get("text") or "").strip() or (caption.get("description") or "").strip()
            if body:
                texts.setdefault(edge["target"], []).append(body)

        return {node_id: " ".join(parts) for node_id, parts in texts.items()}

    @staticmethod
    def export(result: PaperParsingResult, output_dir: Path | str, *, include_report: bool = False) -> Path:
        """Write the parsed document to ``output_dir``.

        Always writes ``document.md`` (the linearized text) and ``graph.json``
        (image crops stripped). With ``include_report=True`` the raw element
        report is also written to ``report.json``.
        """
        destination = Path(output_dir)
        logger.info("Exporting paper parsing artifacts to %s", destination)
        destination.mkdir(parents=True, exist_ok=True)

        document_path = destination / "document.md"
        document_path.write_text(result.markdown, encoding="utf-8")
        save_graph(result.graph, str(destination / "graph.json"))

        if include_report:
            report = [{k: v for k, v in elem.items() if k != "image_bytes"} for elem in result.report]
            (destination / "report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

        logger.info("Paper parsing export completed: %s", document_path)
        return document_path
