"""Repository quality operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repository_quality_scorer import RepositoryQualityScorer

__all__ = ["RepositoryQualityScorer"]


def __getattr__(name: str) -> type[RepositoryQualityScorer]:
    if name == "RepositoryQualityScorer":
        from .repository_quality_scorer import RepositoryQualityScorer

        return RepositoryQualityScorer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
