import json

from osa_tool.tools.paper_claims.batch import collect_pdf_inputs
from osa_tool.tools.paper_claims.evaluate import compute_semantic_matching, load_claims


def test_collect_pdf_inputs_deduplicates_and_reports_invalid(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    text = tmp_path / "notes.txt"
    text.write_text("no")

    paths, failures = collect_pdf_inputs([tmp_path, pdf, text])

    assert paths == [pdf.resolve()]
    assert len(failures) == 1


def test_load_claims_accepts_clean_schema(tmp_path):
    llm = tmp_path / "llm.json"
    human = tmp_path / "human.json"
    llm.write_text(json.dumps({"claims": [{"original_text": "Claim A"}]}))
    human.write_text(json.dumps({"claims": ["Claim A"]}))

    assert load_claims(llm, human) == (["Claim A"], ["Claim A"])


def test_empty_semantic_matching_does_not_load_optional_dependencies():
    metrics = compute_semantic_matching([], ["human"])

    assert metrics["num_matched"] == 0
    assert metrics["matching"] == "many_to_one"
