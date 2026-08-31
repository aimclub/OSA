"""
RepositoryQualityScorer — OSA's formal repository quality scorer.

It reuses OSA's already-cloned repository and produces the existing formal
0–100 quality-report structure. Paper extraction and claim verification belong
to the composed ``paper_analysis`` operation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandlerFactory
from osa_tool.operations.analysis.artifacts import StageReportMetadata, model_provenance, write_stage_report
from osa_tool.utils.logger import logger

from .checks import RepositoryQualityChecker, RepositoryQualityConfig, build_file_tree
from .scoring_engine import RepositoryQualityScoringEngine


class RepositoryQualityScorer:
    """Run formal repository quality scoring without paper or claim processing."""

    def __init__(
        self,
        config_manager: ConfigManager,
        git_agent: GitAgent,
        output_dir: str | None = None,
    ):
        self._config_manager = config_manager
        self._git_agent = git_agent
        self._output_dir = output_dir or os.getcwd()

        model_settings = config_manager.get_model_settings("repository_quality")
        configured_model = getattr(model_settings, "model", None)
        self._configured_model = configured_model if isinstance(configured_model, str) else None
        model_handler = ModelHandlerFactory.build(model_settings)

        self._repository_quality_config = RepositoryQualityConfig(
            clone_dir=git_agent.clone_dir,
            repo_url=str(config_manager.config.git.repository),
            repo=git_agent.repo,
            model_handler=model_handler,
        )

    def get_quality_report(self) -> dict:
        """Run quality checks only and return the report dict.

        Does not save files, does not process a paper or claims.
        Intended for embedding the repository-quality section into another report.
        """
        config = self._repository_quality_config
        logger.info(f"Repository quality checks: {config.repo_url}")
        flat_paths, all_paths = build_file_tree(config.clone_dir)
        checks = RepositoryQualityChecker(config).run_all(flat_paths, all_paths)
        return RepositoryQualityScoringEngine(config.repo_url).build_report(checks)

    def get_model_provenance(self):
        """Return model provenance for the most recent quality-scoring run."""
        return model_provenance(self._repository_quality_config.model_handler, configured=self._configured_model)

    def export_report(
        self,
        report: dict[str, Any],
        output_dir: str | Path,
        *,
        source: dict[str, Any] | None = None,
    ) -> tuple[Path, Path]:
        """Write the module-owned quality artifact without changing the raw score contract."""
        destination = Path(output_dir)
        json_path = write_stage_report(
            destination,
            meta=StageReportMetadata(
                source=source or {"repository": report.get("repo_url", self._repository_quality_config.repo_url)},
                model=self.get_model_provenance(),
            ),
            result=report,
        )
        text_path = destination / "report.txt"
        text_path.write_text(
            RepositoryQualityScoringEngine(report["repo_url"]).build_text_report(report), encoding="utf-8"
        )
        logger.info("Repository quality report saved: %s", json_path)
        logger.info("               : %s", text_path)
        return json_path, text_path

    def run(self) -> dict:
        config = self._repository_quality_config
        scorer = RepositoryQualityScoringEngine(config.repo_url)

        logger.info(f"Repository quality scoring: {config.repo_url}")

        logger.info("Building file tree from local clone...")
        flat_paths, all_paths = build_file_tree(config.clone_dir)

        logger.info("Running quality checks...")
        checks = RepositoryQualityChecker(config).run_all(flat_paths, all_paths)
        report = scorer.build_report(checks)

        output_dir = Path(self._output_dir) / scorer._sanitize_dir_name(config.repo_url)
        json_path, txt_path = self.export_report(report, output_dir)

        print("\n" + scorer.build_text_report(report), file=sys.stderr)

        return {
            "result": {
                "json_path": json_path,
                "txt_path": txt_path,
                "score": report["summary"]["score"],
            }
        }
