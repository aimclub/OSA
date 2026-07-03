import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Flowable,
)

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.operations.analysis.repository_report.report_generator import TextGenerator, AfterReportTextGenerator
from osa_tool.operations.analysis.repository_report.report_localization import ReportTranslationManager
from osa_tool.scheduler.plan import Plan
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root


class AbstractReportGenerator(ABC):
    def __init__(self, config_manager: ConfigManager, git_agent: GitAgent, target_language: str):
        assets_dir = os.path.join(osa_project_root(), "assets")
        pdfmetrics.registerFont(TTFont("notosanssc", os.path.join(assets_dir, "notosans-sc.ttf")))
        pdfmetrics.registerFont(TTFont("notosanssc-Bold", os.path.join(assets_dir, "notosans-sc-bold.ttf")))
        pdfmetrics.registerFont(TTFont("notosanssc-Black", os.path.join(assets_dir, "notosans-sc-black.ttf")))

        # 2. Регистрируем для него отдельное семейство (чтобы ReportLab не выдавал ошибок при попытке применить теги)
        pdfmetrics.registerFontFamily(
            "notosanssc-black",
            normal="notosanssc-Black",
            bold="notosanssc-Black",
            italic="notosanssc-Black",
            boldItalic="notosanssc-Black",
        )

        pdfmetrics.registerFontFamily(
            "notosanssc",
            normal="notosanssc",
            bold="notosanssc-Bold",
            italic="notosanssc",
            boldItalic="notosanssc-Bold",
        )

        self.sourcerank = SourceRank(config_manager)
        self.git_agent = git_agent
        self.metadata = self.git_agent.metadata
        self.repo_url = config_manager.get_git_settings().repository
        self.osa_url = "https://github.com/aimclub/OSA"

        self.logo_path = os.path.join(osa_project_root(), "docs", "images", "osa_logo.PNG")

        self.filename = f"{self.metadata.name}_report.pdf"
        self.output_path = os.path.join(os.getcwd(), self.filename)
        self.start_log = f"Starting analysis for repository {self.metadata.full_name}"
        self.translator = ReportTranslationManager(target_language)
        self.target_language = target_language
        self.report_header = self.translator.get("report_header")

    @staticmethod
    def table_builder(
        data: list,
        w_first_col: int,
        w_second_col: int,
        coloring: bool = False,
    ) -> Table:
        """
        Builds a styled table with customizable column widths and optional row coloring.
        """
        table = Table(data, colWidths=[w_first_col, w_second_col])
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFCCFF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # Выравнивание по центру вертикали
            ("FONTSIZE", (0, 0), (-1, -1), 10),  # Шрифт 10pt для компактности
            ("TOPPADDING", (0, 0), (-1, -1), 3),  # Компактные вертикальные отступы
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("FONTNAME", (0, 0), (-1, -1), "notosanssc"),
            ("FONTNAME", (0, 0), (-1, 0), "notosanssc-Bold"),
        ]
        if coloring:
            for row_idx, row in enumerate(data[1:], start=1):
                cell_val = row[1]
                value = cell_val.text if isinstance(cell_val, Paragraph) else cell_val
                bg_color = colors.lightgreen if value == "✓" else colors.lightcoral
                style.append(("BACKGROUND", (1, row_idx), (1, row_idx), bg_color))

        table.setStyle(TableStyle(style))
        return table

    def generate_qr_code(self) -> str:
        """
        Generates a QR code for the given URL and saves it as an image file.
        """
        qr = qrcode.make(self.osa_url)
        qr_path = os.path.join(os.getcwd(), "temp_qr.png")
        qr.save(qr_path)
        return qr_path

    def draw_images_and_tables(self, canvas_obj: Canvas, doc: SimpleDocTemplate) -> None:
        """
        Draws images, a QR code, lines, and tables on the given PDF canvas.
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
        canvas_obj.line(30, 520, 570, 520)

        table1, table2 = self.table_generator()

        _, h1 = table1.wrap(120, 200)
        _, h2 = table2.wrap(160, 200)

        target_top_left = 620
        target_top_right = 690

        table1.drawOn(canvas_obj, 58, target_top_left - h1)
        table2.drawOn(canvas_obj, 292, target_top_right - h2)

    def header(self) -> list:
        """
        Generates the header section for the repository analysis report.
        """
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            fontName="notosanssc-black",
            name="LeftAligned",
            parent=styles["Title"],
            alignment=0,
            leftIndent=-20,
        )
        title_line1 = Paragraph(self.report_header, title_style)

        name = self.metadata.name
        if len(self.metadata.name) > 20:
            name = self.metadata.name[:20] + "..."

        title_line2 = Paragraph(
            f"{self.translator.get('for')} <a href='{self.repo_url}' color='#00008B'>{name}</a>",
            title_style,
        )

        elements = [title_line1, title_line2]
        return elements

    def table_generator(self) -> tuple[Table, Table]:
        """
        Generates two tables containing repository statistics and presence of key elements.
        """
        styles = getSampleStyleSheet()

        header_style = ParagraphStyle(
            name="TblHeaderStyle",
            parent=styles["Normal"],
            fontName="notosanssc-Bold",
            fontSize=10,
            leading=12,
            alignment=1,
        )

        cell_left_style = ParagraphStyle(
            name="TblCellLeftStyle",
            parent=styles["Normal"],
            fontName="notosanssc",
            fontSize=10,
            leading=12,
            alignment=0,
        )

        cell_center_style = ParagraphStyle(
            name="TblCellCenterStyle",
            parent=styles["Normal"],
            fontName="notosanssc",
            fontSize=10,
            leading=12,
            alignment=1,
        )

        data1 = [
            [
                Paragraph(f"<b>{self.translator.get('statistics')}</b>", header_style),
                Paragraph(f"<b>{self.translator.get('values')}</b>", header_style),
            ],
            [
                Paragraph(self.translator.get("stars_count"), cell_left_style),
                Paragraph(str(self.metadata.stars_count), cell_center_style),
            ],
            [
                Paragraph(self.translator.get("forks_count"), cell_left_style),
                Paragraph(str(self.metadata.forks_count), cell_center_style),
            ],
            [
                Paragraph(self.translator.get("issues_count"), cell_left_style),
                Paragraph(str(self.metadata.open_issues_count), cell_center_style),
            ],
        ]

        data2 = [
            [
                Paragraph(f"<b>{self.translator.get('metric')}</b>", header_style),
                Paragraph(f"<b>{self.translator.get('values')}</b>", header_style),
            ],
            [
                Paragraph(self.translator.get("readme_presence"), cell_left_style),
                Paragraph("✓" if self.sourcerank.readme_presence() else "✗", cell_center_style),
            ],
            [
                Paragraph(self.translator.get("license_presence"), cell_left_style),
                Paragraph("✓" if self.sourcerank.license_presence() else "✗", cell_center_style),
            ],
            [
                Paragraph(self.translator.get("documentation_presence"), cell_left_style),
                Paragraph("✓" if self.sourcerank.docs_presence() else "✗", cell_center_style),
            ],
            [
                Paragraph(self.translator.get("examples_presence"), cell_left_style),
                Paragraph("✓" if self.sourcerank.examples_presence() else "✗", cell_center_style),
            ],
            [
                Paragraph(self.translator.get("requirements_presence"), cell_left_style),
                Paragraph("✓" if self.sourcerank.requirements_presence() else "✗", cell_center_style),
            ],
            [
                Paragraph(self.translator.get("tests_presence"), cell_left_style),
                Paragraph("✓" if self.sourcerank.tests_presence() else "✗", cell_center_style),
            ],
            [
                Paragraph(self.translator.get("description_presence"), cell_left_style),
                Paragraph("✓" if self.metadata.description else "✗", cell_center_style),
            ],
        ]

        table1 = self.table_builder(data1, 120, 76)
        table2 = self.table_builder(data2, 160, 76, True)
        return table1, table2

    def body_first_part(self) -> ListFlowable:
        """
        Generates the first part of the body content for the repository report.
        """
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            fontName="notosanssc",
            name="LeftAlignedNormal",
            parent=styles["Normal"],
            fontSize=12,
            leading=16,
            alignment=0,
        )
        name = self.metadata.name
        if len(self.metadata.name) > 16:
            name = self.metadata.name[:16] + "..."

        repo_link = Paragraph(
            f"{self.translator.get('repository_name')}: <a href='{self.repo_url}' color='#00008B'>{name}</a>",
            normal_style,
        )
        owner_link = Paragraph(
            f"{self.translator.get('owner')}: <a href='{self.metadata.owner_url}' color='#00008B'>{self.metadata.owner}</a>",
            normal_style,
        )
        if self.metadata.created_at:
            try:
                created_at_text = datetime.strptime(self.metadata.created_at, "%Y-%m-%dT%H:%M:%SZ").strftime(
                    "%d.%m.%Y %H:%M"
                )
            except ValueError:
                created_at_text = self.metadata.created_at
        else:
            created_at_text = "N/A"
        created_at = Paragraph(f"{self.translator.get('created_at')}: {created_at_text}", normal_style)

        bullet_list = ListFlowable(
            [
                ListItem(repo_link, leftIndent=-20),
                ListItem(owner_link, leftIndent=-20),
                ListItem(created_at, leftIndent=-20),
            ],
            bulletType="bullet",
        )
        return bullet_list

    @staticmethod
    def get_styles() -> tuple[ParagraphStyle, ParagraphStyle]:
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            fontName="notosanssc",
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
            fontName="notosanssc",
            spaceBefore=6,
            spaceAfter=2,
        )
        return normal_style, custom_style

    @abstractmethod
    def body_second_part(self) -> list[Flowable]:
        pass

    def build_pdf(self) -> None:
        """
        Generates and builds the PDF report for the repository analysis.
        """
        logger.info(self.start_log)

        try:
            doc = SimpleDocTemplate(
                self.output_path,
                pagesize=A4,
                topMargin=50,
                bottomMargin=40,
            )
            doc.build(
                [
                    *self.header(),
                    Spacer(0, 40),
                    self.body_first_part(),
                    Spacer(0, 130),
                    *self.body_second_part(),
                ],
                onFirstPage=self.draw_images_and_tables,
            )
            logger.info(f"PDF report successfully created in {self.output_path}")
        except Exception as e:
            logger.error("Error while building PDF report, %s", e, exc_info=True)


class ReportGenerator(AbstractReportGenerator):

    def __init__(
        self, config_manager: ConfigManager, git_agent: GitAgent, create_fork: bool, target_language: str = "English"
    ):
        super().__init__(config_manager, git_agent, target_language)
        self.text_generator = TextGenerator(config_manager, self.metadata, target_language)
        self.create_fork = create_fork
        self.events: list[OperationEvent] = []

    def run(self) -> dict:
        try:
            self.build_pdf()
            self.events.append(OperationEvent(kind=EventKind.GENERATED, target=f"{self.filename}"))
            if self.create_fork and os.path.exists(self.output_path):
                self.git_agent.upload_report(self.filename, self.output_path)
                self.events.append(OperationEvent(kind=EventKind.UPLOADED, target=f"{self.filename}"))
            return {"result": {"report": self.filename}, "events": self.events}
        except ValueError as e:
            self.events.append(
                OperationEvent(kind=EventKind.FAILED, target="Report generation", data={"error": str(e)})
            )
            return {"result": {"error": str(e)}, "events": self.events}

    def body_second_part(self) -> list[Flowable]:
        """
        Generates the second part of the report, which contains the analysis of the repository.
        """
        parsed_report = self.text_generator.make_request()
        normal_style, custom_style = self.get_styles()
        story = []

        # Repository Structure
        story.append(Paragraph(f"<b>{self.translator.get('repository_structure')}</b>", custom_style))
        story.append(
            Paragraph(f"• {self.translator.get('compliance')}: {parsed_report.structure.compliance}", normal_style)
        )
        if parsed_report.structure.missing_files:
            missing_files = ", ".join(parsed_report.structure.missing_files)
            story.append(Paragraph(f"• {self.translator.get('missing_files')}: {missing_files}", normal_style))
        story.append(
            Paragraph(f"• {self.translator.get('organization')}: {parsed_report.structure.organization}", normal_style)
        )

        # README Analysis
        story.append(Paragraph(f"<b>{self.translator.get('readme_analysis')}:</b>", custom_style))
        story.append(
            Paragraph(f"• {self.translator.get('quality')}: {parsed_report.readme.readme_quality}", normal_style)
        )

        for field_name, value in parsed_report.readme.model_dump().items():
            if field_name == "readme_quality":
                continue

            story.append(
                Paragraph(
                    f"• {self.translator.get(field_name)}: {self.translator.yes_no_partial(value)}",
                    normal_style,
                )
            )

        # Documentation
        story.append(Paragraph(f"<b>{self.translator.get('documentation')}:</b>", custom_style))
        story.append(
            Paragraph(
                f"• {self.translator.get('test_present')}: {self.translator.yes_no_partial(parsed_report.documentation.tests_present)}",
                normal_style,
            )
        )
        story.append(
            Paragraph(
                f"• {self.translator.get('documentation_quality')}: {parsed_report.documentation.docs_quality}",
                normal_style,
            )
        )
        story.append(
            Paragraph(
                f"• {self.translator.get('outdated_content')}: {self.translator.get('yes') if parsed_report.documentation.outdated_content else self.translator.get('no')}",
                normal_style,
            )
        )

        if parsed_report.assessment.key_shortcomings:
            story.append(Paragraph(f"<b>{self.translator.get('key_shortcomings')}:</b>", custom_style))
            for shortcoming in parsed_report.assessment.key_shortcomings:
                story.append(Paragraph(f"  - {shortcoming}", normal_style))

        # Recommendations
        story.append(Paragraph(f"<b>{self.translator.get('recommendations')}:</b>", custom_style))
        for rec in parsed_report.assessment.recommendations:
            story.append(Paragraph(f"  - {rec}", normal_style))

        return story


class WhatHasBeenDoneReportGenerator(AbstractReportGenerator):

    def __init__(
        self,
        config_manager: ConfigManager,
        git_agent: GitAgent,
        create_fork: bool,
        plan: Plan,
        target_language: str = "English",
    ):
        super().__init__(config_manager, git_agent, target_language)
        self.filename = f"{self.metadata.name}_work_summary.pdf"
        self.create_fork = create_fork
        self.output_path = os.path.join(os.getcwd(), self.filename)
        self.completed_tasks = plan.list_for_report
        self.task_results = plan.results or {}
        self.text_generator = AfterReportTextGenerator(
            config_manager, self.completed_tasks, self.task_results, target_language
        )
        self.start_log = f"Starting creating summary for OSA work"
        self.report_header = self.translator.get("summary_header")
        self.events: list[OperationEvent] = []

    def run(self) -> dict:
        try:
            self.build_pdf()
            self.events.append(OperationEvent(kind=EventKind.GENERATED, target=self.filename))
            if self.create_fork and os.path.exists(self.output_path):
                self.git_agent.upload_report(self.filename, self.output_path)
                self.events.append(OperationEvent(kind=EventKind.UPLOADED, target=f"{self.filename}"))
            return {"result": {"report": self.filename}, "events": self.events}
        except ValueError as e:
            self.events.append(OperationEvent(kind=EventKind.FAILED, target="OSA work summary", data={"error": str(e)}))
            return {"result": {"error": str(e)}, "events": self.events}

    def body_second_part(self) -> list[Flowable]:
        """
        Generates the second part of the report, which contains the steps for improving repository taken by the OSA.
        """
        response = self.text_generator.make_request()
        normal_style, custom_style = self.get_styles()
        story = []
        story.append(Paragraph(f"<b>{self.translator.get('what_have_been_done')}:</b>", custom_style))
        story.append(Paragraph(response.summary, normal_style))
        story.append(Paragraph(f"<b>{self.translator.get('report_by_tasks')}:</b>", custom_style))
        for block in response.blocks:
            story.append(Paragraph(f"<b>{block.name}</b>", custom_style))
            story.append(Paragraph(block.description, normal_style))
            for task, was_do in block.tasks:
                task_result = self.translator.get("yes") if was_do else self.translator.get("no")
                story.append(
                    Paragraph(
                        f"• {self.translator.get(task)}: {task_result}",
                        normal_style,
                    )
                )
        return story
