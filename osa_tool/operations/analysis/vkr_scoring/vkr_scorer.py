"""
VkrScorer — OSA operation that runs VKR-style repository quality scoring.

Reuses OSA's already-cloned repository (via GitAgent), its ModelHandler for LLM
calls, and pdfplumber (already in OSA requirements) for PDF parsing.

Steps:
  1. Build file tree from the local clone (no extra GitHub API calls).
  2. Run quality checks: README, license, commits, LLM-based entry-points / repo
     type / tests / data files / experiment scripts, syntax, docstrings.
  3. Obtain claims either by parsing a paper (PDF → sections → LLM extraction)
     or, if already available, by loading a pre-extracted claims JSON file
     directly — skipping PDF parsing and extraction entirely.
  4. Verify claims against code.
  5. Save JSON + text reports, and a PDF report bundling score + claims, to output_dir.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandlerFactory
from osa_tool.operations.analysis.repository_validation.report_generator import (
    ReportGenerator as ValidationReportGenerator,
)
from osa_tool.utils.logger import logger

from .checks import VkrChecker, VkrConfig, build_file_tree
from .claims import ClaimsPipeline
from .scoring_engine import ScoringEngine

# Imported lazily inside _verify_claims_semantic(): CodeAnalyzer/GraphContextRetriever
# pull in torch/transformers, which the default (non-semantic) --vkr-score path doesn't need.


class VkrScorer:
    """Runs VKR repository quality scoring as an OSA operation."""

    def __init__(
        self,
        config_manager: ConfigManager,
        git_agent: GitAgent,
        paper_path: Optional[str] = None,
        claims_path: Optional[str] = None,
        output_dir: Optional[str] = None,
        semantic: bool = False,
    ):
        """
        Args:
            paper_path: Path to a paper PDF. Ignored if `claims_path` is set.
            claims_path: Path to a JSON file with pre-extracted claims — either
                a plain claim array, or a previously saved `claims_analysis`
                report (`{"claims": [...], "stats": {...}}`). When set, PDF
                parsing and LLM-based claim extraction are skipped entirely
                and the claims go straight to verification against the repo.
            semantic: If True, verify claims against code using the repository
                code graph + embedding-based retrieval (same retrieval strategy
                as PaperValidator) instead of the default heuristic file
                selection. One LLM call per claim rather than one batched call
                for all claims — slower and more expensive, but each claim is
                verified against code chosen by semantic relevance.
        """
        self._config_manager = config_manager
        self._git_agent = git_agent
        self._paper_path = paper_path
        self._claims_path = claims_path
        self._output_dir = output_dir or os.getcwd()
        self._semantic = semantic

        model_settings = config_manager.get_model_settings("validation")
        model_handler = ModelHandlerFactory.build(model_settings)

        self._vkr_config = VkrConfig(
            clone_dir=git_agent.clone_dir,
            repo_url=str(config_manager.config.git.repository),
            repo=git_agent.repo,
            model_handler=model_handler,
        )

    def get_quality_report(self) -> dict:
        """Run quality checks only and return the report dict.

        Does not save files, does not process a paper or claims.
        Intended for embedding the VKR score section into another report
        (e.g. the Paper Validation PDF).
        """
        config = self._vkr_config
        logger.info(f"VKR quality checks: {config.repo_url}")
        flat_paths, all_paths = build_file_tree(config.clone_dir)
        checks = VkrChecker(config).run_all(flat_paths, all_paths)
        return ScoringEngine(config.repo_url).build_report(checks)

    def run(self) -> dict:
        config = self._vkr_config
        scorer = ScoringEngine(config.repo_url)

        logger.info(f"VKR scoring: {config.repo_url}")

        logger.info("Building file tree from local clone...")
        flat_paths, all_paths = build_file_tree(config.clone_dir)

        logger.info("Running quality checks...")
        checks = VkrChecker(config).run_all(flat_paths, all_paths)
        report = scorer.build_report(checks)

        if self._paper_path or self._claims_path:
            pipeline = ClaimsPipeline(config)
            claims = self._get_claims(pipeline)
            if claims:
                logger.info(f"Verifying {len(claims)} claims against repository...")
                if self._semantic:
                    report["claims_analysis"] = self._verify_claims_semantic(pipeline, claims, flat_paths)
                else:
                    report["claims_analysis"] = pipeline.verify(claims, flat_paths)
            else:
                logger.warning("No claims extracted from paper.")
                report["claims_analysis"] = {
                    "claims": [],
                    "stats": {
                        "total": 0,
                        "implemented": 0,
                        "implementation_rate": 0.0,
                        "implementation_rate_pct": 0,
                    },
                }

        filename_suffix = "_semantic" if self._semantic else ""
        json_path, txt_path = scorer.save_results(report, self._output_dir, filename_suffix=filename_suffix)
        logger.info(f"VKR report saved: {json_path}")
        logger.info(f"               : {txt_path}")

        print("\n" + scorer.build_text_report(report), file=sys.stderr)

        pdf_path = self._build_pdf_report(report)

        return {
            "result": {
                "json_path": json_path,
                "txt_path": txt_path,
                "pdf_path": pdf_path,
                "score": report["summary"]["score"],
            }
        }

    def _verify_claims_semantic(self, pipeline: ClaimsPipeline, claims: list[dict], flat_paths: list[str]) -> dict:
        """Verify claims via the repository code graph + embedding retrieval (--vkr-score-semantic)."""
        from osa_tool.operations.analysis.repository_validation.analyze.code_analyzer import CodeAnalyzer
        from osa_tool.tools.repository_analysis.semantic_retriever import GraphContextRetriever

        logger.info("Building repository code graph for semantic claim retrieval...")
        code_analyzer = CodeAnalyzer(self._config_manager)
        retriever = GraphContextRetriever(code_analyzer.repo_graph)
        return pipeline.verify_semantic(claims, flat_paths, retriever)

    def _build_pdf_report(self, report: dict) -> Optional[str]:
        """Render *report* (quality checks + claims_analysis, if any) to a PDF."""
        try:
            filename_suffix = "_semantic" if self._semantic else ""
            va_re_gen = ValidationReportGenerator(self._config_manager, self._git_agent.metadata, filename_suffix)
            va_re_gen.build_pdf("VKR", vkr_report=report)
        except Exception as e:
            logger.error(f"Failed to build VKR PDF report: {e}")
            return None

        if not os.path.exists(va_re_gen.output_path):
            return None

        logger.info(f"VKR PDF report saved: {va_re_gen.output_path}")
        return va_re_gen.output_path

    def _get_claims(self, pipeline: ClaimsPipeline) -> list[dict]:
        """Return claims to verify, preferring a pre-extracted file over parsing the paper."""
        if self._claims_path:
            return self._load_claims_from_file()

        paper_sections = self._load_paper_sections()
        if not paper_sections:
            return []
        logger.info("Extracting claims from paper...")
        return pipeline.extract(paper_sections)

    def _load_claims_from_file(self) -> list[dict]:
        """Load pre-extracted claims from a JSON file, skipping PDF parsing and LLM extraction.

        Recognized shapes:
          - a plain claim array: `[{"claim": ..., "category": ..., ...}, ...]`
          - this project's own saved report: `{"claims": [...], "stats": {...}}`
          - an external multi-step extraction dump: `{"result": [...],
            "step3_selection": [{"claim_id": ..., ...}, ...]}`, where "result"
            holds the full claim objects and "step3_selection" is the final
            filtered/deduplicated set (referenced by "claim_id"). Only claims
            whose id survived that selection are kept.

        Any leftover per-claim "implementation" verdict from an earlier
        verification run is dropped so claims re-verify cleanly against the
        current repo state.
        """
        path = Path(self._claims_path)
        if not path.exists():
            logger.warning(f"Claims file does not exist: {self._claims_path}")
            return []

        logger.info(f"Loading pre-extracted claims: {self._claims_path}")
        data = json.loads(path.read_text(encoding="utf-8"))

        if isinstance(data, list):
            claims = data
        elif isinstance(data, dict):
            if "claims" in data:
                claims = data["claims"]
            elif "result" in data:
                claims = data["result"]
                selected_ids = {
                    c.get("claim_id") for c in data.get("step3_selection", []) if isinstance(c, dict)
                }
                if selected_ids:
                    claims = [c for c in claims if not isinstance(c, dict) or c.get("claim_id") in selected_ids]
            else:
                logger.warning(f"Unrecognized claims file structure: {self._claims_path}")
                return []
        else:
            logger.warning(f"Claims file does not contain a JSON array or object: {self._claims_path}")
            return []

        if not isinstance(claims, list):
            logger.warning(f"Claims file does not contain a JSON array: {self._claims_path}")
            return []

        return [{k: v for k, v in claim.items() if k != "implementation"} for claim in claims if isinstance(claim, dict)]

    def _load_paper_sections(self) -> Optional[list[dict]]:
        if not self._paper_path:
            return None

        path = Path(self._paper_path)
        if not path.exists():
            logger.warning(f"Paper path does not exist: {self._paper_path}")
            return None

        logger.info(f"Parsing paper: {self._paper_path}")
        from .pdf_parser import parse_pdf_to_sections

        sections = parse_pdf_to_sections(path.read_bytes())
        logger.info(f"Parsed {len(sections)} sections from paper.")

        sections_out = Path(self._output_dir) / "paper_sections.json"
        sections_out.parent.mkdir(parents=True, exist_ok=True)
        sections_out.write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Paper sections saved: {sections_out}")
        return sections
