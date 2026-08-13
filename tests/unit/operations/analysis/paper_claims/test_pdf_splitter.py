from pathlib import Path

import pytest
from reportlab.pdfgen.canvas import Canvas

from osa_tool.operations.analysis.paper_claims.exceptions import PdfInputError
from osa_tool.operations.analysis.paper_claims.pdf_splitter import PdfChunker


def create_pdf(path: Path, pages: int) -> None:
    canvas = Canvas(str(path))
    for page in range(pages):
        canvas.drawString(50, 750, f"Page {page + 1}")
        canvas.showPage()
    canvas.save()


def test_split_uses_ten_page_boundaries_and_cleans_up(tmp_path):
    pdf = tmp_path / "paper.pdf"
    create_pdf(pdf, 21)

    with PdfChunker() as chunker:
        work_dir = chunker.work_dir
        chunks = chunker.split(pdf)
        assert [(item.start_page, item.end_page) for item in chunks] == [(1, 10), (11, 20), (21, 21)]
        assert all(item.path.exists() for item in chunks)
        assert len({item.source_hash for item in chunks}) == 1

    assert not work_dir.exists()


def test_split_rejects_non_pdf_signature(tmp_path):
    path = tmp_path / "fake.pdf"
    path.write_text("not a pdf")

    with pytest.raises(PdfInputError, match="signature"):
        PdfChunker().split(path)
