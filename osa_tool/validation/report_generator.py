import json
import os

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.utils import logger, osa_project_root


class ReportGenerator:
    def __init__(self, config_loader: ConfigLoader, metadata: RepositoryMetadata, sourcerank: SourceRank) -> None:
        self.config = config_loader.config
        self.sourcerank = sourcerank
        self.repo_url = self.config.git.repository
        self.metadata = metadata

        self.osa_url = "https://github.com/aimclub/OSA"
        self.logo_path = os.path.join(osa_project_root(), "docs", "images", "osa_logo.PNG")

        self.filename = f"{self.metadata.name}_validation_report.pdf"
        self.output_path = os.path.join(os.getcwd(), self.filename)

    def build_pdf(self, type: str, content: str):
        parsed_content = json.loads(content)
        logger.info(f"Building validation report for repository {self.metadata.full_name} ...")
        try:
            doc = SimpleDocTemplate(
                self.output_path,
                pagesize=A4,
                topMargin=50,
                bottomMargin=40,
            )
            doc.build(
                [
                    *self._build_header(type),
                    Spacer(0, 40),
                    *self._build_first_part(parsed_content["correspondence"], parsed_content["percentage"]),
                    Spacer(0, 35),
                    *self._build_second_part(parsed_content["conclusion"]),
                ],
                onFirstPage=self._draw_images,
            )
            logger.info(f"PDF report successfully created in {self.output_path}")
        except Exception as e:
            logger.error("Error while building PDF report, %s", e, exc_info=True)

    def _draw_images(self, canvas_obj: Canvas, doc: SimpleDocTemplate) -> None:
        # Logo OSA
        canvas_obj.drawImage(self.logo_path, 335, 700, width=130, height=120)
        canvas_obj.linkURL(self.osa_url, (335, 700, 465, 820), relative=0)

        # QR OSA
        qr_path = self._generate_qr_code()
        canvas_obj.drawImage(qr_path, 450, 707, width=100, height=100)
        canvas_obj.linkURL(self.osa_url, (450, 707, 550, 807), relative=0)
        os.remove(qr_path)

        # Lines
        canvas_obj.setStrokeColor(colors.black)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(30, 705, 570, 705)
        canvas_obj.line(30, 640, 570, 640)

    def _generate_qr_code(self) -> str:
        """
        Generates a QR code for the given URL and saves it as an image file.

        Returns:
            str: The file path of the generated QR code image.
        """
        qr = qrcode.make(self.osa_url)
        qr_path = os.path.join(os.getcwd(), "temp_qr.png")
        qr.save(qr_path)  # type: ignore
        return qr_path

    def _build_header(self, type: str) -> list:
        """
        Generates the header section for the repository analysis report.

        Returns:
            list: A list of Paragraph elements representing the header content.
        """
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name="LeftAligned",
            parent=styles["Title"],
            alignment=0,
            leftIndent=-20,
        )
        title_line1 = Paragraph(f"{type} Validation Report", title_style)

        name = self.metadata.name
        if len(self.metadata.name) > 20:
            name = self.metadata.name[:20] + "..."

        title_line2 = Paragraph(
            f"for <a href='{self.repo_url}' color='#00008B'>{name}</a>",
            title_style,
        )

        elements = [title_line1, title_line2]
        return elements

    def _build_first_part(self, correspondence: bool, percentages: float) -> list[Paragraph]:
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            name="LeftAlignedNormal",
            parent=styles["Normal"],
            fontSize=12,
            leading=16,
            alignment=0,
        )
        correspondence_text = Paragraph(f"<b>Correspondence: {'Yes' if correspondence  else 'No'}</b>", normal_style)
        percentages_text = Paragraph(f"<b>Percentages: {percentages}%</b>", normal_style)
        return [correspondence_text, percentages_text]

    def _build_second_part(self, conclusion: str) -> list[Flowable]:
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            name="LeftAlignedNormal",
            parent=styles["Normal"],
            fontSize=12,
            leading=16,
            alignment=0,
        )
        conclusion_header = Paragraph("<b>Conclusion:</b>", normal_style)
        conclusion_text = Paragraph(
            conclusion,
            normal_style,
        )
        return [conclusion_header, Spacer(0, 5), conclusion_text]
