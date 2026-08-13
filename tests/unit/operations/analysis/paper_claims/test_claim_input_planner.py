import logging
from types import SimpleNamespace

from osa_tool.operations.analysis.paper_claims.claim_input_planner import ClaimInputPlanner
from osa_tool.operations.analysis.paper_claims.models import HeadingMeta, PaperSection
from tests.unit.operations.analysis.paper_claims.fixtures import (
    make_paper_section as section,
    word_token_count as fake_token_count,
)


class FakeWordCodec:
    @staticmethod
    def encode(text):
        return text.split()

    @staticmethod
    def decode(tokens):
        return " ".join(tokens)


class FakeCharCodec:
    @staticmethod
    def encode(text):
        return [char for char in text for _copy in range(2)]

    @staticmethod
    def decode(tokens):
        return "".join(tokens)


def test_section_ancestors_use_numbering_when_marker_flattens_heading_levels():
    sections = [
        PaperSection(
            section_id="s001",
            name="Introduction",
            text="Intro.",
            heading_meta=HeadingMeta(raw="1 Introduction", level=1, numbering="1"),
        ),
        PaperSection(
            section_id="s002",
            name="Background",
            text="Background.",
            heading_meta=HeadingMeta(raw="1.1 Background", level=1, numbering="1.1"),
        ),
        PaperSection(
            section_id="s003",
            name="Prior Systems",
            text="Prior systems.",
            heading_meta=HeadingMeta(raw="1.1.1 Prior Systems", level=1, numbering="1.1.1"),
        ),
    ]

    ancestors = ClaimInputPlanner(None).section_ancestors(sections)

    assert [item.section_id for item in ancestors["s002"]] == ["s001"]
    assert [item.section_id for item in ancestors["s003"]] == ["s001", "s002"]


def test_section_selection_batches_keep_all_candidates_and_ancestor_context(monkeypatch):
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_input_planner.count_tokens",
        fake_token_count,
    )
    sections = [
        PaperSection(
            section_id="s001",
            name="Method",
            text="Parent section.",
            heading_meta=HeadingMeta(raw="2. Method", level=1, numbering="2"),
        )
    ]
    for index in range(2, 18):
        sections.append(
            PaperSection(
                section_id=f"s{index:03d}",
                name=f"Detailed implementation subsection {index} " + "token " * 30,
                text=f"Section {index}.",
                heading_meta=HeadingMeta(raw=f"2.{index - 1}. Detail", level=2, numbering=f"2.{index - 1}"),
            )
        )

    settings = SimpleNamespace(context_window=520, max_tokens=100, encoder="fake")
    planner = ClaimInputPlanner(settings)
    batches = planner.section_selection_batches(sections, system="system " * 100)

    assert len(batches) > 1
    assert [item.section_id for batch in batches for item in batch.candidate_sections] == [
        item.section_id for item in sections
    ]
    assert any(
        any(item.section_id == "s001" for item in batch.context_sections)
        and all(item.section_id != "s001" for item in batch.candidate_sections)
        for batch in batches
    )


def test_section_chunks_token_count_non_latin_text_before_skipping_split(monkeypatch):
    def fake_count_tokens(text, _encoder="fake"):
        return len(text) * 2 if "🙂" in text else len(text.split())

    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_input_planner.count_tokens",
        fake_count_tokens,
    )
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_input_planner._get_encoder",
        lambda _name: FakeCharCodec(),
    )
    text = "🙂" * 50
    settings = SimpleNamespace(context_window=950, max_tokens=100, encoder="fake")
    planner = ClaimInputPlanner(settings)

    chunks = planner.section_chunks(section(text), system="")

    section_budget = 950 - 100 - 256 - planner.repair_reserve_tokens()
    assert len(text) < section_budget
    assert fake_count_tokens(text) > section_budget
    assert len(chunks) > 1


def test_section_chunks_preserve_complete_sentences_across_boundaries(monkeypatch):
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_input_planner.count_tokens",
        fake_token_count,
    )
    first_sentence = " ".join(["alpha"] * 20) + ". "
    boundary_sentence = " ".join(["boundary"] * 70) + ". "
    final_sentence = " ".join(["omega"] * 20) + "."
    settings = SimpleNamespace(context_window=950, max_tokens=100, encoder="fake")
    chunks = ClaimInputPlanner(settings).section_chunks(
        section(first_sentence + boundary_sentence + final_sentence),
        system="",
    )

    chunk_texts = [chunk.text for chunk in chunks]
    assert len(chunks) > 1
    assert any(boundary_sentence.strip() in chunk for chunk in chunk_texts)
    assert all("boundary boundary" not in chunk or boundary_sentence.strip() in chunk for chunk in chunk_texts)


def test_section_chunks_warn_and_token_split_oversized_single_sentence(monkeypatch, caplog):
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_input_planner.count_tokens",
        fake_token_count,
    )
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_input_planner._get_encoder",
        lambda _name: FakeWordCodec(),
    )
    oversized_sentence = " ".join(["oversized"] * 120) + "."
    planner = ClaimInputPlanner(None)

    with caplog.at_level(logging.WARNING, logger="rich"):
        chunks = planner._sentence_chunks(section(oversized_sentence), budget=50, encoder="fake")

    assert len(chunks) > 1
    assert "falling back to token split" in caplog.text
