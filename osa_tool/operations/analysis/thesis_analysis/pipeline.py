"""Composition of OSA quality scoring, typed paper claims, and claim verification."""

from __future__ import annotations

import json
from time import perf_counter
from pathlib import Path
from typing import Any, Callable

from osa_tool.config.settings import ConfigManager, ThesisPaperClaimsSettings, ThesisVerificationSettings
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandlerFactory
from osa_tool.operations.analysis.paper_claims import LoadedClaimsArtifact, PaperClaimPipeline, PdfChunker
from osa_tool.operations.analysis.repository_quality.checks import build_file_tree
from osa_tool.operations.analysis.repository_quality.repository_quality_scorer import RepositoryQualityScorer
from osa_tool.utils.logger import logger

from .models import (
    PaperClaimsSummary,
    ThesisAnalysisArtifacts,
    ThesisAnalysisMetadata,
    ThesisAnalysisRequest,
    ThesisAnalysisResult,
)
from .verifier import ClaimVerifier

ProgressCallback = Callable[[str, float], None] | None


class ThesisAnalysisOperation:
    """Canonical, non-scheduler operation for a thesis and its repository."""

    def __init__(
        self,
        config_manager: ConfigManager,
        git_agent: GitAgent,
        request: ThesisAnalysisRequest,
        *,
        paper_pipeline_factory: Callable[[Any], PaperClaimPipeline] = PaperClaimPipeline,
        verifier_factory: Callable[[str | Path, Any, ThesisVerificationSettings], ClaimVerifier] = ClaimVerifier,
    ) -> None:
        self._config_manager = config_manager
        self._git_agent = git_agent
        self._request = request
        self._paper_pipeline_factory = paper_pipeline_factory
        self._verifier_factory = verifier_factory

    def run(self, *, on_progress: ProgressCallback = None) -> ThesisAnalysisResult:
        """Create JSON/text artifacts and return their typed canonical result."""
        settings = self._config_manager.get_thesis_analysis_settings()
        output_dir = self._resolve_output_dir()
        claim_input = self._run_stage(
            "Claim input preflight",
            0.0,
            0.05,
            self._preflight_claim_input,
            on_progress,
        )
        quality_scorer = RepositoryQualityScorer(self._config_manager, self._git_agent)
        quality, quality_json_path, quality_text_path = self._run_stage(
            "Repository quality scoring",
            0.05,
            0.30,
            lambda: self._score_and_export(quality_scorer, output_dir),
            on_progress,
        )
        flat_paths = self._run_stage(
            "Repository file-tree collection",
            0.30,
            0.35,
            lambda: build_file_tree(self._git_agent.clone_dir)[0],
            on_progress,
        )
        paper_handler = (
            ModelHandlerFactory.build(self._config_manager.get_model_settings("paper_claims"))
            if self._request.paper_path is not None
            else None
        )
        claims, paper_summary = self._run_stage(
            "Paper-claim extraction" if self._request.paper_path is not None else "Claim-artifact loading",
            0.35,
            0.60,
            lambda: self._load_claims(output_dir, paper_handler, settings.paper_claims, claim_input),
            on_progress,
        )
        verification_handler = ModelHandlerFactory.build(self._config_manager.get_model_settings("thesis_verification"))
        verifier = self._verifier_factory(self._git_agent.clone_dir, verification_handler, settings.verification)
        verification, verification_json_path = self._run_stage(
            "Claim verification",
            0.60,
            0.95,
            lambda: self._verify_and_export(
                verifier,
                claims,
                flat_paths,
                output_dir,
                on_progress,
            ),
            on_progress,
        )

        json_path = output_dir / "thesis_analysis.json"
        text_path = output_dir / "thesis_analysis.txt"
        result = ThesisAnalysisResult(
            meta=ThesisAnalysisMetadata(
                source=self._source_metadata(),
                models={
                    "repository_quality": quality_scorer.get_model_provenance(),
                    "paper_claims": paper_summary.model,
                    "claim_verification": verifier.get_model_provenance(),
                },
            ),
            repository_quality=quality,
            paper_claims=paper_summary,
            claim_verification=verification,
            artifacts=ThesisAnalysisArtifacts(
                json_path=json_path,
                text_path=text_path,
                paper_claims_report_path=paper_summary.artifacts["report_json"],
                paper_claims_claims_path=paper_summary.artifacts["claims_json"],
                repository_quality_json_path=quality_json_path,
                repository_quality_text_path=quality_text_path,
                claim_verification_json_path=verification_json_path,
            ),
        )
        self._run_stage(
            "Writing canonical artifacts",
            0.95,
            1.0,
            lambda: self._write_artifacts(result),
            on_progress,
        )
        return result

    def _score_and_export(
        self,
        scorer: RepositoryQualityScorer,
        output_dir: Path,
    ) -> tuple[dict[str, Any], Path, Path]:
        quality = scorer.get_quality_report()
        json_path, text_path = scorer.export_report(
            quality,
            output_dir / "repository_quality",
            source={"repository": self._request.repository},
        )
        return quality, json_path, text_path

    def _verify_and_export(
        self,
        verifier: ClaimVerifier,
        claims: list[dict[str, Any]],
        flat_paths: list[str],
        output_dir: Path,
        on_progress: ProgressCallback,
    ) -> tuple[Any, Path]:
        verification = verifier.verify(
            claims,
            flat_paths,
            only_high_medium_verifiability=self._request.only_high_medium_verifiability,
            hide_low_confidence=self._request.hide_low_confidence,
            on_progress=lambda message, fraction: self._progress(
                on_progress,
                message,
                0.60 + 0.35 * fraction,
            ),
        )
        report_path = verifier.export(
            verification,
            output_dir / "claim_verification",
            source=self._source_metadata(),
        )
        return verification, report_path

    def _source_metadata(self) -> dict[str, Any]:
        if self._request.paper_path is not None:
            paper = {"kind": "pdf", "path": str(self._request.paper_path)}
        else:
            paper = {"kind": "claims_json", "path": str(self._request.claims_path)}
        return {"repository": self._request.repository, "paper": paper}

    def _load_claims(
        self,
        output_dir: Path,
        handler: Any | None,
        paper_claim_settings: ThesisPaperClaimsSettings,
        claim_input: LoadedClaimsArtifact | Path,
    ) -> tuple[list[dict[str, Any]], PaperClaimsSummary]:
        paper_output_dir = output_dir / "paper_claims"
        if self._request.claims_path is not None:
            assert isinstance(claim_input, LoadedClaimsArtifact)
            loaded = claim_input
            claims_path = PaperClaimPipeline.export_loaded_claims(loaded, paper_output_dir)
            return loaded.claims, PaperClaimsSummary(
                source_kind="claims_json",
                source_path=self._request.claims_path,
                claim_count=len(loaded.claims),
                model=PaperClaimPipeline.model_provenance_for_loaded(loaded),
                artifacts={
                    "claims_json": claims_path,
                    "report_json": paper_output_dir / "report.json",
                },
            )

        assert self._request.paper_path is not None
        assert handler is not None
        assert isinstance(claim_input, Path)
        pipeline = self._paper_pipeline_factory(handler)
        pipeline_result = pipeline.run(
            claim_input,
            paper_claim_settings.to_pipeline_options(),
            show_progress=False,
        )
        claims_path = pipeline.export(pipeline_result, paper_output_dir, legacy=False)
        claims = [claim.model_dump(mode="json") for claim in pipeline_result.extraction.claims]
        return claims, PaperClaimsSummary(
            source_kind="pdf",
            source_path=self._request.paper_path,
            claim_count=len(claims),
            model=PaperClaimPipeline.model_provenance_for_extraction(pipeline_result),
            artifacts={
                "claims_json": claims_path,
                "report_json": paper_output_dir / "report.json",
                "document_markdown": paper_output_dir / "document.md",
                "sections_json": paper_output_dir / "sections.json",
            },
        )

    def _preflight_claim_input(self) -> LoadedClaimsArtifact | Path:
        """Validate the selected claim source before repository-quality model calls."""
        if self._request.claims_path is not None:
            return PaperClaimPipeline.load_claims_json(self._request.claims_path)
        assert self._request.paper_path is not None
        return PdfChunker.validate_readable(self._request.paper_path)

    @staticmethod
    def load_claims_json(path: Path) -> list[dict[str, Any]]:
        """Compatibility wrapper; claim-artifact parsing is owned by ``paper_claims``."""
        return PaperClaimPipeline.load_claims_json(path).claims

    @staticmethod
    def _write_artifacts(result: ThesisAnalysisResult) -> None:
        result.artifacts.json_path.parent.mkdir(parents=True, exist_ok=True)
        result.artifacts.json_path.write_text(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result.artifacts.text_path.write_text(ThesisAnalysisOperation.build_text_report(result), encoding="utf-8")

    def _resolve_output_dir(self) -> Path:
        """Return an external artifact directory without creating it."""
        clone_dir = Path(self._git_agent.clone_dir).resolve()
        output_dir = self._request.output_dir.expanduser().resolve()
        if output_dir == clone_dir or output_dir.is_relative_to(clone_dir):
            raise ValueError("Thesis-analysis output directory must be outside the analyzed repository")
        return output_dir

    @staticmethod
    def _run_stage(
        name: str,
        start: float,
        finish: float,
        action: Callable[[], Any],
        on_progress: ProgressCallback,
    ) -> Any:
        logger.info("Thesis analysis stage started: %s", name)
        ThesisAnalysisOperation._progress(on_progress, name, start)
        started_at = perf_counter()
        try:
            result = action()
        except Exception:
            logger.exception("Thesis analysis stage failed: %s", name)
            ThesisAnalysisOperation._progress(on_progress, f"{name} failed", start)
            raise
        logger.info("Thesis analysis stage completed: %s (%.2fs)", name, perf_counter() - started_at)
        ThesisAnalysisOperation._progress(on_progress, name, finish)
        return result

    @staticmethod
    def _progress(callback: ProgressCallback, message: str, fraction: float) -> None:
        if callback:
            callback(message, min(max(fraction, 0.0), 1.0))

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
