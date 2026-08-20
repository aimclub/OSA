"""Composition of OSA quality scoring, typed paper claims, and claim verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandlerFactory
from osa_tool.operations.analysis.paper_claims import PaperClaimPipeline
from osa_tool.operations.analysis.vkr_scoring.checks import build_file_tree
from osa_tool.operations.analysis.vkr_scoring.vkr_scorer import VkrScorer

from .models import PaperClaimsSummary, ThesisAnalysisArtifacts, ThesisAnalysisRequest, ThesisAnalysisResult
from .verifier import ClaimVerifier


class ThesisAnalysisOperation:
    """Canonical, non-scheduler operation for a thesis and its repository."""

    def __init__(
        self,
        config_manager: ConfigManager,
        git_agent: GitAgent,
        request: ThesisAnalysisRequest,
        *,
        paper_pipeline_factory: Callable[[Any], PaperClaimPipeline] = PaperClaimPipeline,
        verifier_factory: Callable[[str | Path, Any], ClaimVerifier] = ClaimVerifier,
    ) -> None:
        self._config_manager = config_manager
        self._git_agent = git_agent
        self._request = request
        self._paper_pipeline_factory = paper_pipeline_factory
        self._verifier_factory = verifier_factory

    def run(self) -> ThesisAnalysisResult:
        """Create JSON/text artifacts and return their typed canonical result."""
        output_dir = self._request.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        quality = VkrScorer(self._config_manager, self._git_agent).get_quality_report()
        flat_paths, _ = build_file_tree(self._git_agent.clone_dir)
        handler = ModelHandlerFactory.build(self._config_manager.get_model_settings("validation"))
        claims, paper_summary = self._load_claims(output_dir, handler)
        verification = self._verifier_factory(self._git_agent.clone_dir, handler).verify(
            claims,
            flat_paths,
            only_high_medium_verifiability=self._request.only_high_medium_verifiability,
            hide_low_confidence=self._request.hide_low_confidence,
        )

        json_path = output_dir / "thesis_analysis.json"
        text_path = output_dir / "thesis_analysis.txt"
        result = ThesisAnalysisResult(
            repository_quality=quality,
            paper_claims=paper_summary,
            claim_verification=verification,
            artifacts=ThesisAnalysisArtifacts(json_path=json_path, text_path=text_path),
        )
        json_path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
        text_path.write_text(self.build_text_report(result), encoding="utf-8")
        return result

    def _load_claims(self, output_dir: Path, handler: Any) -> tuple[list[dict[str, Any]], PaperClaimsSummary]:
        if self._request.claims_path is not None:
            claims = self.load_claims_json(self._request.claims_path)
            return claims, PaperClaimsSummary(
                source_kind="claims_json",
                source_path=self._request.claims_path,
                claim_count=len(claims),
            )

        assert self._request.paper_path is not None
        pipeline = self._paper_pipeline_factory(handler)
        pipeline_result = pipeline.run(self._request.paper_path)
        paper_output_dir = output_dir / "paper_claims"
        claims_path = pipeline.export(pipeline_result, paper_output_dir, legacy=False)
        claims = [claim.model_dump(mode="json") for claim in pipeline_result.extraction.claims]
        return claims, PaperClaimsSummary(
            source_kind="pdf",
            source_path=self._request.paper_path,
            claim_count=len(claims),
            artifacts={
                "claims_json": claims_path,
                "document_markdown": paper_output_dir / "document.md",
                "sections_json": paper_output_dir / "sections.json",
            },
        )

    @staticmethod
    def load_claims_json(path: Path) -> list[dict[str, Any]]:
        """Accept typed ``claims.json``, legacy ``claims_legacy.json``, or a bare list."""
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(payload, list):
            claims = payload
        elif isinstance(payload, dict):
            claims = payload.get("claims", payload.get("result"))
        else:
            claims = None
        if not isinstance(claims, list) or any(not isinstance(item, dict) for item in claims):
            raise ValueError("Claims JSON must contain a list under 'claims' or 'result', or be a list itself")
        return claims

    @staticmethod
    def build_text_report(result: ThesisAnalysisResult) -> str:
        """Render a compact stable text summary from the canonical JSON result."""
        quality = result.repository_quality.get("summary", {})
        stats = result.claim_verification.stats
        return "\n".join(
            [
                f"Repository: {result.repository_quality.get('repo_url', '')}",
                f"Repository quality score: {quality.get('score', 'n/a')}/100",
                f"Claim source: {result.paper_claims.source_kind} ({result.paper_claims.source_path})",
                f"Source claims: {stats.source_total}",
                f"Eligible claims: {stats.eligible_total}",
                f"Reported claims: {stats.total}",
                f"Implemented claims: {stats.implemented}/{stats.total} ({stats.implementation_rate_pct}%)",
                "",
            ]
        )
