from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from osa_tool.operations.analysis.paper_claims.claim_schemas import ClaimCandidateResponse
from osa_tool.operations.analysis.paper_claims.models import PaperSection
from osa_tool.utils.logger import logger

_SENTENCE_END_CHARACTERS = ".!?…。！？"
_FUZZY_SOURCE_MIN_CHARS = 40
_FUZZY_SOURCE_MIN_SCORE = 94.0
_FUZZY_SOURCE_AMBIGUITY_MARGIN = 2.0
_MIN_RELIABLE_CONTEXT_SCRIPT_LETTERS = 20
_MIN_RELIABLE_CLAIM_SCRIPT_LETTERS = 6
_MIN_SCRIPT_DOMINANCE = 0.70


@dataclass(frozen=True)
class _SourceTextMatch:
    text: str
    method: str
    similarity: float | None = None


@dataclass(frozen=True)
class _ScriptProfile:
    script: str | None
    letters: int
    dominance: float


def _iter_sentence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for index, character in enumerate(text):
        if character not in _SENTENCE_END_CHARACTERS:
            continue
        end = index + 1
        while end < len(text) and text[end] in "\"'”’»)]}":
            end += 1
        stripped_start = start
        stripped_end = end
        while stripped_start < stripped_end and text[stripped_start].isspace():
            stripped_start += 1
        while stripped_end > stripped_start and text[stripped_end - 1].isspace():
            stripped_end -= 1
        if stripped_start < stripped_end:
            spans.append((stripped_start, stripped_end))
        start = end
        while start < len(text) and text[start].isspace():
            start += 1
    if start < len(text):
        stripped_start = start
        stripped_end = len(text)
        while stripped_start < stripped_end and text[stripped_start].isspace():
            stripped_start += 1
        while stripped_end > stripped_start and text[stripped_end - 1].isspace():
            stripped_end -= 1
        if stripped_start < stripped_end:
            spans.append((stripped_start, stripped_end))
    return spans or [(0, len(text))]


def _candidate_source_spans(section_text: str) -> list[str]:
    sentence_spans = _iter_sentence_spans(section_text)
    candidates: list[str] = []
    for start_index, (start, _end) in enumerate(sentence_spans):
        for window_size in (1, 2):
            end_index = start_index + window_size - 1
            if end_index >= len(sentence_spans):
                continue
            source_text = section_text[start : sentence_spans[end_index][1]]
            if source_text and source_text not in candidates:
                candidates.append(source_text)
    return candidates


def _find_fuzzy_source_match(section_text: str, original_text: str) -> _SourceTextMatch | None:
    if len(original_text.strip()) < _FUZZY_SOURCE_MIN_CHARS:
        return None
    candidates = _candidate_source_spans(section_text)
    if not candidates:
        return None

    matches = process.extract(
        original_text,
        candidates,
        scorer=fuzz.ratio,
        limit=2,
        score_cutoff=_FUZZY_SOURCE_MIN_SCORE,
    )
    if not matches:
        return None

    best_text, best_score, _best_index = matches[0]
    if len(matches) > 1:
        second_text, second_score, _second_index = matches[1]
        if second_text != best_text and best_score - second_score <= _FUZZY_SOURCE_AMBIGUITY_MARGIN:
            logger.debug(
                "Fuzzy original_text repair is ambiguous. best_score=%.1f; second_score=%.1f; "
                "best_text=%r; second_text=%r",
                best_score,
                second_score,
                best_text,
                second_text,
            )
            return None
    return _SourceTextMatch(best_text, method="fuzzy", similarity=best_score / 100)


def _find_original_source_match(section_text: str, original_text: str) -> _SourceTextMatch | None:
    """Return an exact source span, or a conservative RapidFuzz-backed repair."""
    if original_text in section_text:
        return _SourceTextMatch(original_text, method="exact")

    return _find_fuzzy_source_match(section_text, original_text)


def _section_text_preview(text: str, limit: int = 2_000) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n... <{len(text) - limit} characters omitted> ...\n{text[-half:]}"


def _script_profile(text: str) -> _ScriptProfile:
    """Return the dominant Unicode script plus basic confidence metadata."""
    scripts: dict[str, int] = {}
    script_markers = {
        "LATIN": ("LATIN",),
        "CYRILLIC": ("CYRILLIC",),
        "EAST_ASIAN": ("CJK", "HIRAGANA", "KATAKANA", "HANGUL"),
        "ARABIC": ("ARABIC",),
        "HEBREW": ("HEBREW",),
    }
    for character in text:
        if not character.isalpha():
            continue
        unicode_name = unicodedata.name(character, "")
        script = next(
            (script for script, markers in script_markers.items() if any(marker in unicode_name for marker in markers)),
            None,
        )
        if script:
            scripts[script] = scripts.get(script, 0) + 1
    if not scripts:
        return _ScriptProfile(script=None, letters=0, dominance=0.0)
    letters = sum(scripts.values())
    dominant = max(scripts, key=scripts.get)
    return _ScriptProfile(script=dominant, letters=letters, dominance=scripts[dominant] / letters)


def _is_reliable_script(profile: _ScriptProfile, *, min_letters: int) -> bool:
    return profile.script is not None and profile.letters >= min_letters and profile.dominance >= _MIN_SCRIPT_DOMINANCE


def _format_script_profile(profile: _ScriptProfile) -> str:
    return f"{profile.script or 'unknown'} letters={profile.letters} dominance={profile.dominance:.2f}"


def _validate_claim_script(*, item: ClaimCandidateResponse, section: PaperSection, source_text: str) -> None:
    section_profile = _script_profile(section.text)
    source_profile = _script_profile(source_text)
    claim_profile = _script_profile(item.claim)
    if not _is_reliable_script(claim_profile, min_letters=_MIN_RELIABLE_CLAIM_SCRIPT_LETTERS):
        return

    allowed_scripts: set[str] = set()
    if (
        _is_reliable_script(section_profile, min_letters=_MIN_RELIABLE_CONTEXT_SCRIPT_LETTERS)
        and section_profile.script
    ):
        allowed_scripts.add(section_profile.script)
    if _is_reliable_script(source_profile, min_letters=_MIN_RELIABLE_CONTEXT_SCRIPT_LETTERS) and source_profile.script:
        allowed_scripts.add(source_profile.script)
    if not allowed_scripts or claim_profile.script in allowed_scripts:
        return

    raise ValueError(
        "claim must use a plausible language script for its section or evidence. "
        f"claim_script={_format_script_profile(claim_profile)}; "
        f"section_script={_format_script_profile(section_profile)}; "
        f"original_text_script={_format_script_profile(source_profile)}; "
        f"claim={item.claim!r}; original_text={source_text!r}"
    )


def validate_claim_candidate(item: ClaimCandidateResponse, *, section: PaperSection) -> None:
    source_match = _find_original_source_match(section.text, item.original_text)
    if source_match is None:
        logger.debug(
            "Source-text validation failed for section %s. Candidate=%r; section_text=%r",
            section.section_id,
            item.original_text,
            section.text,
        )
        raise ValueError(
            f"original_text is not present in section {section.section_id}. "
            f"original_text={item.original_text!r}; "
            f"section_text_preview={_section_text_preview(section.text)!r}; "
            f"section_text_length={len(section.text)}"
        )
    if source_match.method == "fuzzy":
        logger.info(
            "Repaired original_text in section %s using fuzzy source match (similarity=%.3f)",
            section.section_id,
            source_match.similarity or 0.0,
        )
        logger.debug(
            "Fuzzy original_text repair in section %s: candidate=%r; repaired=%r",
            section.section_id,
            item.original_text,
            source_match.text,
        )
    item.original_text = source_match.text
    _validate_claim_script(item=item, section=section, source_text=source_match.text)


def partition_valid_claim_candidates(
    items: list[ClaimCandidateResponse], *, section: PaperSection
) -> tuple[list[ClaimCandidateResponse], list[str]]:
    valid: list[ClaimCandidateResponse] = []
    invalid: list[str] = []
    for index, item in enumerate(items, start=1):
        try:
            validate_claim_candidate(item, section=section)
            valid.append(item)
        except ValueError as exc:
            invalid.append(f"claim #{index}: {exc}")
    return valid, invalid
