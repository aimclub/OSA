"""
VkrScorer — OSA's formal VKR-style repository quality scorer.

It reuses OSA's already-cloned repository and produces the existing formal
0–100 quality-report structure. Thesis paper extraction and claim verification
belong exclusively to ``thesis_analysis``.
"""

from __future__ import annotations

import os
import sys

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandlerFactory
from osa_tool.utils.logger import logger

from .checks import VkrChecker, VkrConfig, build_file_tree
from .scoring_engine import ScoringEngine


class VkrScorer:
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

        json_path, txt_path = scorer.save_results(report, self._output_dir)
        logger.info(f"VKR report saved: {json_path}")
        logger.info(f"               : {txt_path}")

        print("\n" + scorer.build_text_report(report), file=sys.stderr)

        return {
            "result": {
                "json_path": json_path,
                "txt_path": txt_path,
                "score": report["summary"]["score"],
            }
        }
