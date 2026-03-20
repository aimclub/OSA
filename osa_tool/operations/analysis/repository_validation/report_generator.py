import os

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root


class ReportGenerator:
    """
    Generates a comprehensive PDF validation report detailing the analysis, documentation quality, and structural improvements for a repository.
    
        This class builds a PDF report summarizing repository analysis results, including correspondence,
        percentage metrics, and conclusions. It adds branding, QR codes, and repository metadata to the report.
    """


    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata) -> None:
        """
        Initialize the ReportGenerator.
        
        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences. Used to retrieve the repository URL and other configuration.
            metadata: Metadata about the repository, including its name, which is used to generate the report filename.
        
        The constructor sets up paths and filenames needed for generating a PDF validation report. It extracts the repository URL from the configuration and uses the repository name from metadata to create an output filename. It also defines static references, such as the OSA project URL and logo path, for inclusion in the report.
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
        
        This method orchestrates the creation of a PDF report by assembling predefined sections (header, correspondence metrics, and conclusion) into a single document. It logs the process and handles any errors that occur during PDF generation.
        
        Args:
            type: Type of validation (e.g., "Code", "Doc", "Paper"). This determines the header title.
            content: A dictionary containing the report data. Expected keys are "correspondence", "percentage", and "conclusion", which are passed to the respective helper methods for section building.
        
        Why:
            The report provides a formatted, persistent record of the validation analysis for the repository, making the results easily shareable and reviewable. The PDF is saved to a predefined output path for later access.
        
        Note:
            The method uses a fixed page layout (A4 with specified margins) and includes a custom background image on the first page via the `onFirstPage` callback.
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
                    *self._build_header(type),
                    Spacer(0, 40),
                    *self._build_first_part(content["correspondence"], content["percentage"]),
                    Spacer(0, 35),
                    *self._build_second_part(content["conclusion"]),
                ],
                onFirstPage=self._draw_images,
            )
            logger.info(f"PDF report successfully created in {self.output_path}")
        except Exception as e:
            logger.error("Error while building PDF report, %s", e, exc_info=True)

    def _draw_images(self, canvas_obj: Canvas, doc: SimpleDocTemplate) -> None:
        """
        Draws branding images, QR code, and lines on the first page of the PDF.
        Specifically, it places the OSA logo and a QR code linking to the OSA Tool report URL, and adds two horizontal lines for visual separation.
        The QR code is generated temporarily for this purpose and deleted after being drawn.
        
        Args:
            canvas_obj: The canvas object for drawing.
            doc: The PDF document template.
        
        Returns:
            None
        """
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
        Generates a QR code for the OSA Tool report URL and saves it as a temporary image file.
        The QR code is created from the `osa_url` instance attribute, which contains the URL to the generated report, allowing for easy sharing and access.
        
        Args:
            None: This method uses the instance's `osa_url` attribute as the data for the QR code.
        
        Returns:
            str: The absolute file path to the generated QR code image (saved as "temp_qr.png" in the current working directory).
        """
        qr = qrcode.make(self.osa_url)
        qr_path = os.path.join(os.getcwd(), "temp_qr.png")
        qr.save(qr_path)  # type: ignore
        return qr_path

    def _build_header(self, type: str) -> list:
        """
        Generates the header section for the repository analysis report.
        
        Args:
            type: Type of validation (e.g., "Code", "Doc", "Paper"). This determines the first line of the header, such as "Code Validation Report".
        
        Returns:
            A list of Paragraph elements representing the header content. The list contains two Paragraphs:
            - The first displays the validation type as a title.
            - The second shows a truncated repository name (if longer than 20 characters) as a clickable hyperlink to the repository URL, styled consistently with the first line.
        
        Why:
            The header provides a clear, formatted title for the report and links directly to the analyzed repository, improving accessibility and context. The repository name is truncated to maintain clean formatting in the report layout.
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

    @staticmethod
    def _build_first_part(correspondence: bool, percentages: float) -> list[Paragraph]:
        """
        Builds the first section of the report with correspondence and percentage metrics.
        
        This section presents a high-level summary of whether the repository content aligns with its associated documentation or paper, along with a quantitative measure of that alignment. The output is formatted as styled paragraphs suitable for inclusion in a generated report.
        
        Args:
            correspondence: Indicates whether the repository corresponds to the documentation or paper. A value of True means the repository content matches the described work; False indicates a discrepancy.
            percentages: A percentage metric quantifying the degree of correspondence. This value is displayed directly in the report as a percentage.
        
        Returns:
            A list containing two Paragraph objects: the first states the correspondence result, and the second displays the percentage metric. Both are styled for consistent report formatting.
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
        return [correspondence_text, percentages_text]

    @staticmethod
    def _build_second_part(conclusion: str) -> list[Flowable]:
        """
        Builds the conclusion section of the report.
        
        Args:
            conclusion: Conclusion text for the report. This text will be formatted as a paragraph with normal styling.
        
        Returns:
            list[Flowable]: Flowable elements for the section, consisting of:
                - A bold "Conclusion:" header paragraph.
                - A small vertical spacer (5 units).
                - A paragraph containing the provided conclusion text.
            The elements are styled with a custom ParagraphStyle ("LeftAlignedNormal") based on the reportlab normal style, using 12pt font size, 16pt leading, and left alignment.
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
        return [conclusion_header, Spacer(0, 5), conclusion_text]
