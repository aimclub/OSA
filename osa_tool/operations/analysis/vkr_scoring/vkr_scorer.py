"""
VkrScorer — OSA operation that runs VKR-style repository quality scoring.

Reuses OSA's already-cloned repository (via GitAgent), its ModelHandler for LLM
calls, and pdfplumber (already in OSA requirements) for PDF parsing.

Steps:
  1. Build file tree from the local clone (no extra GitHub API calls).
  2. Run quality checks: README, license, commits, LLM-based entry-points / repo
     type / tests / data files / experiment scripts, syntax, docstrings.
  3. If a paper path is provided: parse PDF → extract claims → verify against code.
  4. Save JSON + text reports to output_dir.
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
from osa_tool.utils.logger import logger

from .checks import VkrConfig, build_file_tree, run_all_checks
from .claims import extract_claims, verify_claims
from .report import build_report, build_text_report, save_results


class VkrScorer:
    """Runs VKR repository quality scoring as an OSA operation."""

    def __init__(
        self,
        config_manager: ConfigManager,
        git_agent: GitAgent,
        paper_path: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        self._config_manager = config_manager
        self._git_agent = git_agent
        self._paper_path = paper_path
        self._output_dir = output_dir or os.getcwd()

        model_settings = config_manager.get_model_settings("validation")
        model_handler = ModelHandlerFactory.build(model_settings)

        self._vkr_config = VkrConfig(
            clone_dir=git_agent.clone_dir,
            repo_url=str(config_manager.config.git.repository),
            repo=git_agent.repo,
            model_handler=model_handler,
        )

    def run(self) -> dict:
        config = self._vkr_config
        logger.info(f"VKR scoring: {config.repo_url}")

        logger.info("Building file tree from local clone...")
        flat_paths, all_paths = build_file_tree(config.clone_dir)

        logger.info("Running quality checks...")
        checks = run_all_checks(flat_paths, all_paths, config)
        report = build_report(checks, config.repo_url)

        paper_sections = self._load_paper_sections()
        if paper_sections:
            logger.info("Extracting claims from paper...")
            claims = extract_claims(paper_sections, config)
            if claims:
                logger.info(f"Verifying {len(claims)} claims against repository...")
                report["claims_analysis"] = verify_claims(claims, flat_paths, config)
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

        json_path, txt_path = save_results(report, self._output_dir)
        logger.info(f"VKR report saved: {json_path}")
        logger.info(f"               : {txt_path}")

        print("\n" + build_text_report(report), file=sys.stderr)

        return {
            "result": {
                "json_path": json_path,
                "txt_path": txt_path,
                "score": report["summary"]["score"],
            }
        }

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
