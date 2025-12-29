import os
from typing import Iterable

import qrcode
from osa_tool.core.git.metadata import RepositoryMetadata
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

from osa_tool.config.settings import ConfigManager
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root


class ReportGenerator:
    """
    Generates a PDF validation report for a repository.

    This class builds a PDF report summarizing repository analysis results, including correspondence,
    percentage metrics, and conclusions. It adds branding, QR codes, and repository metadata to the report.
    """

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata) -> None:
        """
        Initialize the ReportGenerator.

        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
            metadata (RepositoryMetadata): Metadata about the repository.
        """
        self.config_manager = config_manager
        self.repo_url = self.config_manager.get_git_settings().repository
        self.metadata = metadata

        self.osa_url = "https://github.com/aimclub/OSA"
        self.logo_path = os.path.join(osa_project_root(), "docs", "images", "osa_logo.PNG")

        self.filename = f"{self.metadata.name}_validation_report.pdf"
        self.output_path = os.path.join(os.getcwd(), self.filename)

    def build_pdf(self, type: str, content: dict) -> None:
        """
        Build and save the PDF validation report.

        Args:
            type (str): Type of validation (e.g., "Code", "Doc", "Paper").
            content (dict): JSON containing report data.

        Returns:
            None
        """
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
                    *self.__build_header(type),
                    Spacer(0, 40),
                    *self.__build_brief(content["correspondence"], content["percentage"]),
                    Spacer(0, 35),
                    *self.__build_table(content["assessment"]),
                    *self.__build_conclusion(content["conclusion"]),
                ],
                onFirstPage=self.__draw_images,
            )
            logger.info(f"PDF report successfully created in {self.output_path}")
        except Exception as e:
            logger.error("Error while building PDF report, %s", e, exc_info=True)

    def __draw_images(self, canvas_obj: Canvas, doc: SimpleDocTemplate) -> None:
        """
        Draws branding images, QR code, and lines on the first page of the PDF.

        Args:
            canvas_obj (Canvas): The canvas object for drawing.
            doc (SimpleDocTemplate): The PDF document template.

        Returns:
            None
        """
        # Logo OSA
        canvas_obj.drawImage(self.logo_path, 335, 700, width=130, height=120)
        canvas_obj.linkURL(self.osa_url, (335, 700, 465, 820), relative=0)

        # QR OSA
        qr_path = self.__generate_qr_code()
        canvas_obj.drawImage(qr_path, 450, 707, width=100, height=100)
        canvas_obj.linkURL(self.osa_url, (450, 707, 550, 807), relative=0)
        os.remove(qr_path)

        # Lines
        canvas_obj.setStrokeColor(colors.black)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(30, 705, 570, 705)
        canvas_obj.line(30, 640, 570, 640)

    def __generate_qr_code(self) -> str:
        """
        Generates a QR code for the given URL and saves it as an image file.

        Returns:
            str: The file path of the generated QR code image.
        """
        qr = qrcode.make(self.osa_url)
        qr_path = os.path.join(os.getcwd(), "temp_qr.png")
        qr.save(qr_path)  # type: ignore
        return qr_path

    def __build_header(self, type: str) -> tuple:
        """
        Generates the header section for the repository analysis report.

        Args:
            type (str): Type of validation (e.g., "Code", "Doc", "Paper").

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

        return title_line1, title_line2

    @staticmethod
    def __build_brief(correspondence: bool, percentages: float) -> tuple:
        """
        Builds the first section of the report with correspondence and percentage metrics.

        Args:
            correspondence (bool): Whether the repository corresponds to the documentation/paper.
            percentages (float): Percentage metric for correspondence.

        Returns:
            list[Paragraph]: Paragraph elements for the section.
        """
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
        return correspondence_text, percentages_text

    @staticmethod
    def __build_table(results: list[dict]) -> Iterable[Paragraph]:
        return (
            Paragraph(
                f"""<b>Experiment {i + 1}.</b>
                <b>Formulation stated: </b><p>"{elem['proposed_experiment_description']}"</p>
                <b>Assessment: </b><p>{elem['assessment']}</p>
                """
            )
            for i, elem in enumerate(results)
        )

    @staticmethod
    def __build_conclusion(self, conclusion: str) -> tuple:
        """
        Builds the conclusion section of the report.

        Args:
            conclusion (str): Conclusion text for the report.

        Returns:
            list[Flowable]: Flowable elements for the section.
        """
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
        return Spacer(0, 10), conclusion_header, Spacer(0, 5), conclusion_text
