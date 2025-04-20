import logging
import os
from datetime import datetime

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from rich.logging import RichHandler

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.report_generator import TextGenerator
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.readmeai.config.settings import ConfigLoader
from osa_tool.readmeai.readmegen_article.config.settings import ArticleConfigLoader
from osa_tool.utils import osa_project_root

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)

logger = logging.getLogger("rich")


class ReportGenerator:
    def __init__(self,
                 config_loader: ConfigLoader | ArticleConfigLoader,
                 sourcerank: SourceRank,
                 output_path: str = None):
        self.config = config_loader.config
        self.sourcerank = sourcerank
        self.text_generator = TextGenerator(config_loader, self.sourcerank)
        self.repo_url = self.config.git.repository
        self.osa_url = "https://github.com/ITMO-NSS-team/Open-Source-Advisor"
        self.metadata = load_data_metadata(self.repo_url)

        self.logo_path = os.path.join(
            osa_project_root(),
            "docs",
            "images",
            "osa_logo.PNG"
        )

        self.filename = f"{self.metadata.name}_report.pdf"
        self.output_path = os.path.join(
            output_path or os.getcwd(),
            self.filename
        )

    @staticmethod
    def table_builder(
            data: list,
            w_first_col: int,
            w_second_col: int,
            coloring: bool = False,
    ) -> Table:
        """
        Builds a styled table with customizable column widths and optional row coloring.

        Args:
            data (List): The table data, where the first row is treated as a header.
            w_first_col (int): The width of the first column.
            w_second_col (int): The width of the second column.
            coloring (bool, optional): If True, applies conditional row coloring based on
                                   the values in the second column. Defaults to False.

        Returns:
            Table: A formatted table with applied styles.
        """
        table = Table(data, colWidths=[w_first_col, w_second_col])
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFCCFF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]
        if coloring:
            for row_idx, row in enumerate(data[1:], start=1):
                value = row[1]
                bg_color = colors.lightgreen if value == "✓" else colors.lightcoral
                style.append(
                    ("BACKGROUND", (1, row_idx), (1, row_idx), bg_color))

        table.setStyle(TableStyle(style))
        return table

    def generate_qr_code(self) -> str:
        """
        Generates a QR code for the given URL and saves it as an image file.

        Returns:
            str: The file path of the generated QR code image.
        """
        qr = qrcode.make(self.osa_url)
        qr_path = os.path.join(os.getcwd(), "temp_qr.png")
        qr.save(qr_path)
        return qr_path

    def draw_images_and_tables(
            self,
            canvas_obj: Canvas,
            doc: SimpleDocTemplate
    ) -> None:
        """
        Draws images, a QR code, lines, and tables on the given PDF canvas.

        Args:
            canvas_obj (Canvas): The PDF canvas object to draw on
            doc (SimpleDocTemplate): The PDF document that is being generated. This parameter is not used directly
                                     but is required by the ReportLab framework for page rendering.

        Returns:
            None
        """
        # Logo OSA
        canvas_obj.drawImage(self.logo_path, 335, 700, width=130, height=120)
        canvas_obj.linkURL(self.osa_url, (335, 700, 465, 820), relative=0)

        # QR OSA
        qr_path = self.generate_qr_code()
        canvas_obj.drawImage(qr_path, 450, 707, width=100, height=100)
        canvas_obj.linkURL(self.osa_url, (450, 707, 550, 807), relative=0)
        os.remove(qr_path)

        # Lines
        canvas_obj.setStrokeColor(colors.black)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(30, 705, 570, 705)
        canvas_obj.line(30, 540, 570, 540)

        # Tables
        table1, table2 = self.table_generator()

        table1.wrapOn(canvas_obj, 0, 0)
        table1.drawOn(canvas_obj, 58, 555)

        table2.wrapOn(canvas_obj, 0, 0)
        table2.drawOn(canvas_obj, 292, 555)

    def header(self) -> list:
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
        title_line1 = Paragraph(f"Repository Analysis Report", title_style)
        title_line2 = Paragraph(
            f"for <a href='{self.repo_url}' color='#00008B'>{self.metadata.name}</a>",
            title_style)

        elements = [title_line1, title_line2]
        return elements

    def table_generator(self) -> tuple[Table, Table]:
        """
        Generates two tables containing repository statistics and presence of key elements.

        The first table includes basic repository statistics, and the second table shows
        the presence of important elements such as README, License, Documentation, etc.

        Returns:
            tuple[Table, Table]: A tuple containing two Table objects.
        """
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            name="LeftAlignedNormal",
            parent=styles["Normal"],
            fontSize=12,
            alignment=1,
        )
        data1 = [
            [Paragraph("<b>Statistics</b>", normal_style),
             Paragraph("<b>Values</b>", normal_style)],
            ["Stars Count", str(self.metadata.stars_count)],
            ["Forks Count", str(self.metadata.forks_count)],
            ["Issues Count", str(self.metadata.open_issues_count)],
        ]
        data2 = [
            [Paragraph("<b>Metric</b>", normal_style),
             Paragraph("<b>Values</b>", normal_style)],
            ["README Presence",
             "✓" if self.sourcerank.readme_presence() else "✗"],
            ["License Presence",
             "✓" if self.sourcerank.license_presence() else "✗"],
            ["Documentation Presence",
             "✓" if self.sourcerank.docs_presence() else "✗"],
            ["Examples Presence",
             "✓" if self.sourcerank.examples_presence() else "✗"],
            ["Tests Presence",
             "✓" if self.sourcerank.tests_presence() else "✗"],
            ["Description Presence",
             "✓" if self.metadata.description else "✗"],
        ]
        table1 = self.table_builder(data1, 120, 76)
        table2 = self.table_builder(data2, 160, 76, True)
        return table1, table2

    def body_first_part(self) -> ListFlowable:
        """
        Generates the first part of the body content for the repository report.

        This includes the repository name with a hyperlink, owner information with a hyperlink,
        and the repository creation date. The data is presented as a bulleted list.

        Returns:
            ListFlowable: A ListFlowable object containing a bulleted list of repository details.
        """
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            name="LeftAlignedNormal",
            parent=styles["Normal"],
            fontSize=12,
            leading=16,
            alignment=0,
        )
        repo_link = Paragraph(
            f"Repository Name: <a href='{self.repo_url}' color='#00008B'>{self.metadata.name}</a>",
            normal_style)
        owner_link = Paragraph(
            f"Owner: <a href='{self.metadata.owner_url}' color='#00008B'>{self.metadata.owner}</a>",
            normal_style)
        created_at = Paragraph(
            f"Created at: {datetime.strptime(self.metadata.created_at, '%Y-%m-%dT%H:%M:%SZ').strftime('%d.%m.%Y %H:%M')}",
            normal_style)

        bullet_list = ListFlowable(
            [
                ListItem(repo_link, leftIndent=-20),
                ListItem(owner_link, leftIndent=-20),
                ListItem(created_at, leftIndent=-20),
            ],
            bulletType="bullet"
        )
        return bullet_list

    def body_second_part(self) -> list:
        """
        Generates the second part of the report, which contains the analysis of the repository.

        Returns:
            list: A list of Paragraph objects for the PDF report.
        """
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            name="LeftAlignedNormal",
            parent=styles["Normal"],
            fontSize=12,
            leading=13,
            leftIndent=-20,
            rightIndent=-20,
            alignment=0,
        )
        custom_style = ParagraphStyle(
            name="CustomStyle",
            parent=normal_style,
            spaceBefore=6,
            spaceAfter=2,
        )

        parsed_report = self.text_generator.make_request()

        story = []

        # Repository Structure
        story.append(Paragraph("<b>Repository Structure:</b>", custom_style))
        story.append(
            Paragraph(f"• Compliance: {parsed_report.structure.compliance}",
                      normal_style))
        if parsed_report.structure.missing_files:
            missing_files = ", ".join(parsed_report.structure.missing_files)
            story.append(
                Paragraph(f"• Missing files: {missing_files}", normal_style))
        story.append(Paragraph(
            f"• Organization: {parsed_report.structure.organization}",
            normal_style))

        # README Analysis
        story.append(Paragraph("<b>README Analysis:</b>", custom_style))
        story.append(Paragraph(f"• Quality: {parsed_report.readme.readme_quality}", normal_style))

        for field_name, value in parsed_report.readme.model_dump().items():
            if field_name == "readme_quality":
                continue

            story.append(Paragraph(
                f"• {field_name.replace('_', ' ').capitalize()}: {value.value}",
                normal_style))

        # Documentation
        story.append(Paragraph("<b>Documentation:</b>", custom_style))
        story.append(Paragraph(
            f"• Tests present: {parsed_report.documentation.tests_present.value}",
            normal_style))
        story.append(Paragraph(
            f"• Documentation quality: {parsed_report.documentation.docs_quality}",
            normal_style))
        story.append(Paragraph(
            f"• Outdated content: {'Yes' if parsed_report.documentation.outdated_content else 'No'}",
            normal_style))

        if parsed_report.assessment.key_shortcomings:
            story.append(Paragraph("<b>Key Shortcomings:</b>", custom_style))
            for shortcoming in parsed_report.assessment.key_shortcomings:
                story.append(Paragraph(f"  - {shortcoming}", normal_style))

        # Recommendations
        story.append(Paragraph("<b>Recommendations:</b>", custom_style))
        for rec in parsed_report.assessment.recommendations:
            story.append(Paragraph(f"  - {rec}", normal_style))

        return story

    def build_pdf(self) -> None:
        """
        Generates and builds the PDF report for the repository analysis.

        This method initializes the PDF document, adds the header, body content (first and second parts),
        and then generates the PDF file. The `draw_images_and_tables` method is used to draw images and tables
        on the first page of the document.

        Returns:
            None

        Raises:
            Exception: If there is an error during the PDF creation process.
        """
        logger.info(
            f"Starting analysis for repository {self.metadata.full_name}")

        try:
            doc = SimpleDocTemplate(self.output_path,
                                    pagesize=A4,
                                    topMargin=50,
                                    bottomMargin=40,
                                    leftMaring=10
                                    )
            doc.build(
                [
                    *self.header(),
                    Spacer(0, 40),
                    self.body_first_part(),
                    Spacer(0, 110),
                    *self.body_second_part(),
                ],
                onFirstPage=self.draw_images_and_tables,
            )
            logger.info(
                f"PDF report successfully created in {self.output_path}")
        except Exception as e:
            logger.error("Error while building PDF report, %s", e,
                         exc_info=True)
