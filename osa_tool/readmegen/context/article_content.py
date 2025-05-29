import os
from pathlib import Path

try:
    import aspose.pdf as ap
except Exception as ex:
    print(f"Can not use aspose lib: {ex}. Please note that it can be MacOS-specific issue.")

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTLine, LTTextContainer


class PdfParser:
    """
    Extract text from PDFs excluding table and images text
    """

    def __init__(self, pdf_path: str) -> None:
        self.path = pdf_path

    def data_extractor(self) -> str:
        """
        Extract text from  PDF and return a text.
        """
        path_obj = Path(self.path)
        pages_text = []
        extracted_data = ""
        doc = ap.Document(self.path)
        standard_tables = self.extract_table_bboxes(doc)

        for pagenum, page in enumerate(extract_pages(self.path)):
            verticals, horizontals = self.get_page_lines(page)
            page_text_elements = []

            for element in page:
                if isinstance(element, LTTextContainer):
                    text = element.get_text().strip()
                    if len(text) < 5:
                        continue
                    table_by_lines = self.is_table_text_lines(element, verticals, horizontals)
                    table_by_standard = pagenum in standard_tables and standard_tables[pagenum] and self.is_table_text_standard(element, standard_tables[pagenum])
                    if table_by_lines or table_by_standard:
                        continue
                    page_text_elements.append(text)

            if page_text_elements:
                pages_text.append(" ".join(page_text_elements))

        if pages_text:
            extracted_data = "\n".join(pages_text)

        if path_obj.name.startswith("downloaded_"):
            try:
                os.remove(path_obj)
            except OSError:
                pass

        return extracted_data

    @staticmethod
    def extract_table_bboxes(
        doc
    ) -> dict[int, list[tuple[float, float, float, float]]]:
        """Extract standard table bounding boxes using Aspose."""
        table_bboxes: dict[int, list[tuple[float, float, float, float]]] = {}
        for page_num, page in enumerate(doc.pages):
            absorber = ap.text.TableAbsorber()
            absorber.visit(page)
            boxes = []
            for table in absorber.table_list:
                rect = table.rectangle
                boxes.append((rect.llx, rect.lly, rect.urx, rect.ury))
            if boxes:
                table_bboxes[page_num] = boxes
        return table_bboxes

    @staticmethod
    def get_page_lines(
        page
    ) -> tuple[list[tuple[float, float, float, float]], list[tuple[float, float, float, float]]]:
        """Extract vertical and horizontal lines from a page"""
        verticals = []
        horizontals = []
        for el in page:
            if isinstance(el, LTLine):
                x0, y0, x1, y1 = el.bbox
                if abs(x1 - x0) < 3:
                    verticals.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
                elif abs(y1 - y0) < 3:
                    horizontals.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
        return verticals, horizontals

    @staticmethod
    def is_table_text_lines(
        element,
        verticals: list[tuple[float, float, float, float]],
        horizontals: list[tuple[float, float, float, float]],
        tol: float = 2.0,
    ) -> bool:
        """Check table membership using heuristic lines"""
        x0, y0, x1, y1 = element.bbox
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        vertical_condition = False
        if len(verticals) >= 2:
            union_left = min(v[0] for v in verticals)
            union_right = max(v[2] for v in verticals)
            union_bottom = min(v[1] for v in verticals)
            union_top = max(v[3] for v in verticals)
            if (union_left - tol <= cx <= union_right + tol and
                    union_bottom - tol <= cy <= union_top + tol):
                vertical_condition = True
        horizontal_condition = False
        if len(horizontals) >= 2:
            union_bottom_h = min(h[1] for h in horizontals)
            union_top_h = max(h[3] for h in horizontals)
            if union_bottom_h - tol <= cy <= union_top_h + tol:
                horizontal_condition = True
        return vertical_condition or horizontal_condition

    @staticmethod
    def is_table_text_standard(
        element,
        table_boxes: list[tuple[float, float, float, float]],
        tol: float = 2.0,
    ) -> bool:
        """Check table membership using Aspose standard table boxes"""
        x0, y0, x1, y1 = element.bbox
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for box in table_boxes:
            if (box[0] - tol <= cx <= box[2] + tol and
                    box[1] - tol <= cy <= box[3] + tol):
                return True
        return False
