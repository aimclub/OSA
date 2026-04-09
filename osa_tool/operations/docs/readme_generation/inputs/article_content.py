"""Extract text from PDF files, excluding table regions."""

import os
from pathlib import Path

import pdfplumber
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTLine, LTTextContainer

from osa_tool.utils.logger import logger

Bbox = tuple[float, float, float, float]


class PdfParser:
    """Extract text from PDFs excluding table and image regions."""

    def __init__(self, pdf_path: str) -> None:
        self.path = pdf_path

    def data_extractor(self) -> str:
        """Extract non-table text from every page and return as a single string."""
        path_obj = Path(self.path)
        pages_text: list[str] = []
        with pdfplumber.open(self.path) as doc:
            standard_tables = self.extract_table_bboxes(doc)

            for pagenum, page in enumerate(extract_pages(self.path)):
                verticals, horizontals = self.get_page_lines(page)
                page_text_elements: list[str] = []

                for element in page:
                    if not isinstance(element, LTTextContainer):
                        continue
                    text = element.get_text().strip()
                    if len(text) < 5:
                        continue
                    if self.is_table_text_lines(element, verticals, horizontals):
                        continue
                    page_tables = standard_tables.get(pagenum, [])
                    if page_tables and self.is_table_text_standard(element, page_tables):
                        continue
                    page_text_elements.append(text)

                if page_text_elements:
                    pages_text.append(" ".join(page_text_elements))

        extracted_data = "\n".join(pages_text) if pages_text else ""

        if path_obj.name.startswith("downloaded_"):
            try:
                os.remove(path_obj)
            except OSError:
                logger.warning("Failed to remove temporary PDF file: %s", path_obj, exc_info=True)

        return extracted_data

    @staticmethod
    def extract_table_bboxes(doc: pdfplumber.PDF) -> dict[int, list[Bbox]]:
        """Extract standard table bounding boxes using pdfplumber."""
        table_bboxes: dict[int, list[Bbox]] = {}
        settings = {"horizontal_strategy": "lines", "vertical_strategy": "lines"}
        for page_num, page in enumerate(doc.pages):
            boxes = [table.bbox for table in page.find_tables(table_settings=settings)]
            if boxes:
                table_bboxes[page_num] = boxes
        return table_bboxes

    @staticmethod
    def get_page_lines(page: object) -> tuple[list[Bbox], list[Bbox]]:
        """Separate vertical and horizontal lines from a PDF page layout."""
        verticals: list[Bbox] = []
        horizontals: list[Bbox] = []
        for el in page:
            if not isinstance(el, LTLine):
                continue
            x0, y0, x1, y1 = el.bbox
            if abs(x1 - x0) < 3:
                verticals.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
            elif abs(y1 - y0) < 3:
                horizontals.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
        return verticals, horizontals

    @staticmethod
    def is_table_text_lines(
        element: LTTextContainer,
        verticals: list[Bbox],
        horizontals: list[Bbox],
        tol: float = 2.0,
    ) -> bool:
        """Check if a text element falls inside a region bounded by heuristic lines."""
        x0, y0, x1, y1 = element.bbox
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

        if len(verticals) >= 2:
            union_left = min(v[0] for v in verticals)
            union_right = max(v[2] for v in verticals)
            union_bottom = min(v[1] for v in verticals)
            union_top = max(v[3] for v in verticals)
            if union_left - tol <= cx <= union_right + tol and union_bottom - tol <= cy <= union_top + tol:
                return True

        if len(horizontals) >= 2:
            union_bottom_h = min(h[1] for h in horizontals)
            union_top_h = max(h[3] for h in horizontals)
            if union_bottom_h - tol <= cy <= union_top_h + tol:
                return True

        return False

    @staticmethod
    def is_table_text_standard(
        element: LTTextContainer,
        table_boxes: list[Bbox],
        tol: float = 2.0,
    ) -> bool:
        """Check if a text element overlaps a pdfplumber-detected table box."""
        x0, y0, x1, y1 = element.bbox
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for box in table_boxes:
            if box[0] - tol <= cx <= box[2] + tol and box[1] - tol <= cy <= box[3] + tol:
                return True
        return False
