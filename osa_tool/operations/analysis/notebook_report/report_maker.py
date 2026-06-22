from __future__ import annotations

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, SimpleDocTemplate, TableStyle

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.operations.analysis.notebook_report.analyzer import NotebookReportAnalyzer
from osa_tool.operations.analysis.notebook_report.models import NotebookAnalysisBundle
from osa_tool.operations.analysis.repository_report.report_maker import AbstractReportGenerator


class NotebookReportGenerator(AbstractReportGenerator):
    def __init__(
        self,
        config_manager: ConfigManager,
        git_agent: GitAgent,
        create_fork: bool,
        notebook_paths: list[str] | None = None,
    ) -> None:
        super().__init__(config_manager, git_agent)
        self.filename = f"{self.metadata.name}_notebook_report.pdf"
        self.output_path = os.path.join(os.getcwd(), self.filename)
        self.start_log = f"Starting notebook analysis for repository {self.metadata.full_name}"
        self.report_header = "Notebook Analysis Report"
        self.create_fork = create_fork
        self.notebook_paths = notebook_paths or []
        self.analyzer = NotebookReportAnalyzer(config_manager, self.notebook_paths)
        self.bundle: NotebookAnalysisBundle | None = None
        self.events: list[OperationEvent] = []
        self._first_page_body_spacer = 148

    def run(self) -> dict:
        try:
            self.bundle = self.analyzer.analyze()
            self.events.extend(self.analyzer.events)
            self.build_pdf()
            self.events.append(OperationEvent(kind=EventKind.GENERATED, target=self.filename))
            if self.create_fork and os.path.exists(self.output_path):
                self.git_agent.upload_report(self.filename, self.output_path)
                self.events.append(OperationEvent(kind=EventKind.UPLOADED, target=self.filename))
            return {"result": {"report": self.filename}, "events": self.events}
        except ValueError as exc:
            self.events.append(
                OperationEvent(kind=EventKind.FAILED, target="Notebook report generation", data={"error": str(exc)})
            )
            return {"result": {"error": str(exc)}, "events": self.events}

    def table_generator(self) -> tuple[Table, Table]:
        bundle = self._require_bundle()
        summary = bundle.summary
        label_style, value_style = self._table_cell_styles()

        combined_data = [
            [
                Paragraph("<b>Notebook Summary</b>", label_style),
                Paragraph("<b>Value</b>", value_style),
                Paragraph("<b>Quality Signals</b>", label_style),
                Paragraph("<b>Value</b>", value_style),
            ],
            [
                Paragraph("Total notebooks scanned", label_style),
                Paragraph(str(summary.total_notebooks), value_style),
                Paragraph("Total findings", label_style),
                Paragraph(str(summary.total_issues), value_style),
            ],
            [
                Paragraph("Successfully analyzed", label_style),
                Paragraph(str(summary.analyzed_notebooks), value_style),
                Paragraph("Invalid syntax notebooks", label_style),
                Paragraph(str(summary.invalid_syntax_notebooks), value_style),
            ],
            [
                Paragraph("Read or parse failures", label_style),
                Paragraph(str(summary.failed_notebooks), value_style),
                Paragraph("Fully non-executed notebooks", label_style),
                Paragraph(str(summary.non_executed_notebooks), value_style),
            ],
            [
                Paragraph("Notebooks with findings", label_style),
                Paragraph(str(summary.notebooks_with_issues), value_style),
                Paragraph("Analysis scope", label_style),
                Paragraph(str(len(self.notebook_paths)) if self.notebook_paths else "Repository-wide", value_style),
            ],
        ]
        return self._build_combined_summary_table(combined_data), Table([[""]], colWidths=[0], rowHeights=[0])

    def body_second_part(self) -> list[Flowable]:
        bundle = self._require_bundle()
        normal_style, custom_style, subtle_style = self._notebook_styles()
        story: list[Flowable] = []
        summary = bundle.summary

        story.append(Paragraph("<b>Overview</b>", custom_style))
        story.append(
            Paragraph(
                (
                    f"This report reviewed <b>{summary.total_notebooks}</b> notebook(s) and recorded "
                    f"<b>{summary.total_issues}</b> finding(s) across structure, execution, and readability."
                ),
                normal_style,
            )
        )
        if self.notebook_paths:
            story.append(
                Paragraph(
                    f"Selected targets were provided explicitly: <b>{len(self.notebook_paths)}</b> path(s).",
                    subtle_style,
                )
            )
        else:
            story.append(Paragraph("Scope: full repository notebook scan.", subtle_style))

        if summary.issue_frequencies:
            story.append(Paragraph("<b>Most Frequent Findings</b>", custom_style))
            for slug, count in list(summary.issue_frequencies.items())[:7]:
                story.append(Paragraph(f"• {self._humanize_slug(slug)}: {count}", normal_style))

        story.append(Paragraph("<b>Notebook Details</b>", custom_style))
        for notebook in bundle.notebooks:
            story.append(Paragraph(f"<b>{notebook.relative_path}</b>", custom_style))
            stats = notebook.statistics
            status_parts = []
            if notebook.analysis_errors:
                status_parts.append("analysis errors present")
            elif notebook.issues:
                status_parts.append(f"{len(notebook.issues)} finding(s)")
            else:
                status_parts.append("no findings detected")
            story.append(Paragraph(f"Status: {', '.join(status_parts)}.", subtle_style))
            story.append(
                Paragraph(
                    (
                        f"Cells: total <b>{stats.number_of_cells}</b>, code {stats.number_of_code_cells}, "
                        f"markdown {stats.number_of_markdown_cells}, raw {stats.number_of_raw_cells}"
                    ),
                    normal_style,
                )
            )
            story.append(
                Paragraph(
                    (
                        f"Markdown lines {stats.number_of_markdown_lines}, titles {stats.number_of_markdown_titles}, "
                        f"functions {self._display_optional(stats.number_of_functions)}, "
                        f"classes {self._display_optional(stats.number_of_classes)}"
                    ),
                    subtle_style,
                )
            )

            if notebook.analysis_errors:
                for error in notebook.analysis_errors:
                    story.append(Paragraph(f"• Analysis error: {error}", normal_style))

            if not notebook.issues:
                story.append(Paragraph("• No notebook issues detected.", normal_style))
            else:
                for issue in notebook.issues:
                    line = f"• {issue.description}"
                    if issue.details:
                        line += f" <font color='#555555'>({issue.details})</font>"
                    story.append(Paragraph(line, normal_style))
                    story.append(Paragraph(f"Recommendation: {issue.recommendation}", subtle_style))

            story.append(Spacer(0, 10))

        return story

    def build_pdf(self) -> None:
        from osa_tool.utils.logger import logger

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
                    Spacer(0, 34),
                    self.body_first_part(),
                    Spacer(0, self._first_page_body_spacer),
                    *self.body_second_part(),
                ],
                onFirstPage=self.draw_images_and_tables,
            )
            logger.info("PDF report successfully created in %s", self.output_path)
        except Exception as exc:
            logger.error("Error while building notebook PDF report, %s", exc, exc_info=True)

    def draw_images_and_tables(self, canvas_obj: Canvas, doc: SimpleDocTemplate) -> None:
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
        canvas_obj.line(30, 500, 570, 500)

        # Table
        table1, _ = self.table_generator()
        table1.wrapOn(canvas_obj, 0, 0)
        table1.drawOn(canvas_obj, 37, 510)

    def _build_summary_table(self, data: list[list[Paragraph]], first_col_width: int, second_col_width: int) -> Table:
        table = Table(data, colWidths=[first_col_width, second_col_width], rowHeights=None)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFCCFF")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        return table

    def _build_combined_summary_table(self, data: list[list[Paragraph]]) -> Table:
        table = Table(data, colWidths=[180, 70, 200, 70], rowHeights=None)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (1, 0), colors.lightgrey),
                    ("BACKGROUND", (2, 0), (3, 0), colors.lightgrey),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFCCFF")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (2, 0), (2, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("ALIGN", (3, 0), (3, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        return table

    @staticmethod
    def _table_cell_styles() -> tuple[ParagraphStyle, ParagraphStyle]:
        styles = getSampleStyleSheet()
        label_style = ParagraphStyle(
            name="NotebookTableLabel",
            parent=styles["BodyText"],
            fontSize=9.5,
            leading=11,
            alignment=0,
        )
        value_style = ParagraphStyle(
            name="NotebookTableValue",
            parent=styles["BodyText"],
            fontSize=9.5,
            leading=11,
            alignment=1,
        )
        return label_style, value_style

    def _notebook_styles(self) -> tuple[ParagraphStyle, ParagraphStyle, ParagraphStyle]:
        normal_style, custom_style = self.get_styles()
        subtle_style = ParagraphStyle(
            name="NotebookSubtle",
            parent=normal_style,
            textColor=colors.HexColor("#555555"),
            leading=12,
            spaceAfter=2,
        )
        custom_style = ParagraphStyle(
            name="NotebookSection",
            parent=custom_style,
            fontSize=12.5,
            leading=14,
            spaceBefore=8,
            spaceAfter=4,
        )
        normal_style = ParagraphStyle(
            name="NotebookBody",
            parent=normal_style,
            leading=14,
            spaceAfter=2,
        )
        return normal_style, custom_style, subtle_style

    @staticmethod
    def _humanize_slug(slug: str) -> str:
        return slug.replace("-", " ").replace("_", " ").capitalize()

    @staticmethod
    def _display_optional(value: int | None) -> str:
        return str(value) if value is not None else "N/A"

    def _require_bundle(self) -> NotebookAnalysisBundle:
        if self.bundle is None:
            raise ValueError("Notebook analysis has not been executed yet.")
        return self.bundle
