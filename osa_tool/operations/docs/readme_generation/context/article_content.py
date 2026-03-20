import os
import subprocess
from pathlib import Path

import pdfplumber
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTLine, LTTextContainer


class PdfParser:
    """
    Extract text from PDFs excluding table and images text
    """


    def __init__(self, pdf_path: str) -> None:
        """
        Initializes a new instance of the PdfParser class with a specified PDF file path.
        
        Args:
            pdf_path: The file system path to the PDF document to be parsed.
        
        Attributes:
            path: Stores the file system path to the PDF document. This path is used by other methods in the class to load and process the PDF content.
        
        Note:
            The constructor only stores the file path; actual PDF parsing occurs in other methods when needed. This design allows lazy or on-demand loading of the document.
        """
        self.path = pdf_path

    def data_extractor(self) -> str:
        """
        Extract text from a PDF while excluding content identified as part of tables.
        
        The method processes each page of the PDF to collect text elements, filtering out any text that is determined to belong to a table. Table detection uses two complementary strategies: one based on visible line borders extracted from the page layout, and another using standard table bounding boxes identified by pdfplumber. After processing all pages, the extracted text is concatenated. If the PDF file was downloaded (indicated by a filename starting with "downloaded_"), the method attempts to delete the file after extraction.
        
        Args:
            None (uses the instance's `path` attribute as the PDF file path).
        
        Returns:
            A string containing the concatenated text from all non‑table elements across every page. If no text is extracted, an empty string is returned.
        """
        path_obj = Path(self.path)
        pages_text = []
        extracted_data = ""
        doc = pdfplumber.open(self.path)
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
                    table_by_standard = (
                        pagenum in standard_tables
                        and standard_tables[pagenum]
                        and self.is_table_text_standard(element, standard_tables[pagenum])
                    )
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
    def extract_table_bboxes(doc) -> dict[int, list[tuple[float, float, float, float]]]:
        """
        Extract standard table bounding boxes from each page of a PDF document using pdfplumber.
        
        This method identifies tables by detecting both horizontal and vertical lines on each page,
        then returns the bounding boxes of all found tables. It is useful for locating table regions
        prior to content extraction or layout analysis.
        
        Args:
            doc: A pdfplumber PDF document object containing the pages to be processed.
        
        Returns:
            A dictionary where each key is a page number (zero‑based index) and each value is a list
            of bounding‑box tuples for that page. Each bounding box is a tuple of four floats
            (x0, top, x1, bottom) representing the table’s coordinates in PDF points.
            Pages without tables are omitted from the dictionary.
        """
        table_bboxes: dict[int, list[tuple[float, float, float, float]]] = {}
        table_settings = {"horizontal_strategy": "lines", "vertical_strategy": "lines"}
        for page_num, page in enumerate(doc.pages):
            boxes = []
            tables = page.find_tables(table_settings=table_settings)
            for table in tables:
                boxes.append(table.bbox)
            if boxes:
                table_bboxes[page_num] = boxes
        return table_bboxes

    @staticmethod
    def get_page_lines(
        page,
    ) -> tuple[list[tuple[float, float, float, float]], list[tuple[float, float, float, float]]]:
        """
        Extract vertical and horizontal lines from a page.
        
        Parses a PDF page object to identify line elements, classifying them as vertical or horizontal based on their orientation. This is used to detect table borders or structural lines in document layout analysis.
        
        Args:
            page: An iterable of layout elements from a PDF page (e.g., LTItem objects from pdfminer).
        
        Returns:
            A tuple containing two lists:
                - verticals: List of tuples, each representing a vertical line as (x0, y0, x1, y1) with coordinates normalized to min/max order.
                - horizontals: List of tuples, each representing a horizontal line as (x0, y0, x1, y1) with coordinates normalized to min/max order.
        
        Why:
            Lines are classified by comparing coordinate differences: a line is considered vertical if its x-coordinates are nearly identical (difference < 3 points), and horizontal if its y-coordinates are nearly identical. This threshold helps filter minor drawing inaccuracies while capturing intended table borders or separators.
        """
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
        """
        Check if a text element is part of a table by testing its position relative to detected table lines.
        
        The method uses a heuristic that an element belongs to a table if its center point lies within the bounding region
        formed by either a set of vertical lines or a set of horizontal lines. This is useful for filtering table content
        from other text in a PDF, where tables are often defined by visible ruling lines.
        
        Args:
            element: The text element to check, expected to have a `bbox` attribute representing its bounding box as (x0, y0, x1, y1).
            verticals: A list of vertical line segments, each defined as a tuple (x0, y0, x1, y1).
            horizontals: A list of horizontal line segments, each defined as a tuple (x0, y0, x1, y1).
            tol: Tolerance in coordinate units for matching the element's center to the line union region. Default is 2.0.
        
        Returns:
            True if the element's center lies within the tolerance-adjusted bounding region of at least two vertical lines
            or within the vertical range of at least two horizontal lines; otherwise False.
        """
        x0, y0, x1, y1 = element.bbox
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        vertical_condition = False
        if len(verticals) >= 2:
            union_left = min(v[0] for v in verticals)
            union_right = max(v[2] for v in verticals)
            union_bottom = min(v[1] for v in verticals)
            union_top = max(v[3] for v in verticals)
            if union_left - tol <= cx <= union_right + tol and union_bottom - tol <= cy <= union_top + tol:
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
        """
        Check whether a text element belongs to any table using pdfplumber's standard table bounding boxes.
        
        The method determines membership by checking if the center point of the element's bounding box falls within any of the provided table boxes, allowing a small tolerance for alignment discrepancies.
        
        Args:
            element: A text element with a bbox attribute representing its bounding box coordinates (x0, y0, x1, y1).
            table_boxes: A list of tuples, each defining a table's bounding box as (x0, y0, x1, y1) in PDF coordinate space.
            tol: A tolerance value (in PDF coordinate units) added to each side of a table box to allow for slight misalignments or rounding errors. Default is 2.0.
        
        Returns:
            True if the element's center lies within any table box (including the tolerance margin), otherwise False.
        """
        x0, y0, x1, y1 = element.bbox
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for box in table_boxes:
            if box[0] - tol <= cx <= box[2] + tol and box[1] - tol <= cy <= box[3] + tol:
                return True
        return False

    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """
        Extract text from a PDF file using the pdftotext command-line tool.
        
        Args:
            pdf_path: Path to the PDF file.
        
        Returns:
            Extracted text content as a string.
        
        Raises:
            RuntimeError: If pdftotext fails during execution or is not installed on the system.
        
        Why:
            This method provides a simple, layout-preserving text extraction from PDFs by leveraging the external pdftotext utility (part of poppler-utils). It is used when direct Python PDF parsing libraries are unavailable or insufficient for the required layout fidelity.
        """
        try:
            # TODO: add pdftotext dependency or remove if unused
            result = subprocess.run(
                [
                    "pdftotext",
                    "-layout",
                    "-enc",
                    "UTF-8" "-nopgbrk",
                    str(pdf_path),
                    "-",
                ],
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"pdftotext failed with error: {e.stderr}") from e
        except FileNotFoundError:
            raise RuntimeError("pdftotext not found. Please install poppler-utils.") from None
