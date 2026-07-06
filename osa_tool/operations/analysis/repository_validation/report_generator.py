import os
import xml.sax.saxutils as saxutils

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Register Unicode-aware fonts for Cyrillic support (claim/experiment text may be Russian).
_unicode_font_name = "Helvetica"
try:
    _regular_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Debian/Ubuntu
        "/usr/share/fonts/TTF/DejaVuSans.ttf",  # Arch/Manjaro
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",  # Fedora/RHEL
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # macOS
        "/Library/Fonts/Arial Unicode.ttf",  # macOS (older)
        "C:\\Windows\\Fonts\\arial.ttf",  # Windows fallback
    ]
    _bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]
    _regular_path = next((p for p in _regular_candidates if os.path.exists(p)), None)
    if _regular_path:
        pdfmetrics.registerFont(TTFont("CyrillicFont", _regular_path))
        _bold_path = next((p for p in _bold_candidates if os.path.exists(p)), None)
        if _bold_path:
            pdfmetrics.registerFont(TTFont("CyrillicFont-Bold", _bold_path))
            pdfmetrics.registerFontFamily(
                "CyrillicFont",
                normal="CyrillicFont",
                bold="CyrillicFont-Bold",
                italic="CyrillicFont",
                boldItalic="CyrillicFont-Bold",
            )
        _unicode_font_name = "CyrillicFont"
except Exception:
    pass

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.analysis.repository_validation.models import Experiment
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root

# Labels for weighted repository checks (mirrors vkr_scoring.scoring_engine weights).
_CHECK_LABELS: dict[str, str] = {
    "readme": "README",
    "license": "License",
    "commits": "Commits (>5)",
    "execution_files": "Entry-point files",
    "requirements": "Requirements file",
    "tests": "Tests",
    "data_files": "Data files",
    "experiment_scripts": "Experiment scripts",
}


def _esc(text: object) -> str:
    """Escape text for safe embedding into a reportlab Paragraph's markup."""
    return saxutils.escape(str(text) if text is not None else "")


def _score_color(score: int) -> str:
    if score >= 70:
        return "#27ae60"
    if score >= 40:
        return "#e67e22"
    return "#e74c3c"


class RoundedCard(Flowable):
    def __init__(
        self,
        content: list,
        width: int,
        padding: int = 10,
        radius: int = 8,
        stroke_color=colors.HexColor("#B8C1CC"),
    ) -> None:
        super().__init__()
        self.content = content
        self.width = width
        self.padding = padding
        self.radius = radius
        self.stroke_color = stroke_color
        self._wrapped_content: list[tuple[Flowable, float]] = []
        self._height = 0

    def wrap(self, aW: float, aH: float):
        inner_width = max(1, self.width - (2 * self.padding))
        self._wrapped_content = []

        inner_height = 0.0
        for flowable in self.content:
            _, h = flowable.wrap(inner_width, aH)
            self._wrapped_content.append((flowable, h))
            inner_height += h

        self._height = inner_height + (2 * self.padding)
        return self.width, self._height

    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(self.stroke_color)
        self.canv.setLineWidth(1)
        self.canv.roundRect(0, 0, self.width, self._height, self.radius, stroke=1, fill=0)
        self.canv.restoreState()

        y = self._height - self.padding
        for flowable, h in self._wrapped_content:
            y -= h
            flowable.drawOn(self.canv, self.padding, y)


class ReportGenerator:
    """
    Generates a PDF validation report for a repository.

    This class builds a PDF report summarizing repository analysis results, including correspondence,
    percentage metrics, and conclusions. It adds branding, QR codes, and repository metadata to the report.
    """

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata, filename_suffix: str = "") -> None:
        """
        Initialize the ReportGenerator.

        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
            metadata (RepositoryMetadata): Metadata about the repository.
            filename_suffix (str): Optional suffix distinguishing reports from alternate
                pipeline variants (e.g. "_semantic") run against the same repository, so
                they don't overwrite each other's output when run in the same invocation.
        """
        self.config_manager = config_manager
        self.repo_url = self.config_manager.get_git_settings().repository
        self.metadata = metadata

        self.osa_url = "https://github.com/aimclub/OSA"
        self.logo_path = os.path.join(osa_project_root(), "docs", "images", "osa_logo.PNG")

        self.filename = f"{self.metadata.name}{filename_suffix}_validation_report.pdf"
        self.output_path = os.path.join(os.getcwd(), self.filename)

    def build_pdf(
        self,
        type_: str,
        experiments: tuple[Experiment, ...] = (),
        vkr_report: dict | None = None,
    ) -> None:
        """
        Build and save the PDF validation report.

        Args:
            type_ (str): Type of validation (e.g., "Code", "Doc", "Paper", "VKR").
            experiments (tuple[Experiment]): Assessed experiments, if any. Omitted
                (empty) for a pure VKR quality/claims report with no paper-derived
                experiment breakdown.
            vkr_report (dict | None): Optional VKR quality-check report to include.
                May also carry a "claims_analysis" key (as produced by
                ClaimsPipeline.verify) to render a claims verification section.

        Returns:
            None
        """
        logger.info(f"Building validation report for repository {self.metadata.full_name} ...")
        claims_analysis = (vkr_report or {}).get("claims_analysis")
        try:
            doc = SimpleDocTemplate(
                self.output_path,
                pagesize=A4,
                topMargin=50,
                bottomMargin=40,
            )
            elements = [
                *self.__build_header(type_),
                Spacer(0, 20),
                *self.__build_vkr_section(vkr_report),
                Spacer(0, 20),
                *self.__build_claims_section(claims_analysis),
            ]
            if experiments:
                elements += [
                    Spacer(0, 20),
                    *self.__build_brief(experiments),
                    Spacer(0, 20),
                    *self.__build_table(experiments),
                ]
            try:
                doc.build(elements, onFirstPage=self.__draw_images)
                logger.info(f"PDF report successfully created in {self.output_path}")
            except Exception as layout_error:
                logger.warning(f"Layout error in PDF: {layout_error}. Retrying with simplified format...")
                elements = [
                    *self.__build_header(type_),
                    Spacer(0, 20),
                    *self.__build_vkr_section(vkr_report),
                    Spacer(0, 20),
                    *self.__build_claims_section(claims_analysis),
                ]
                if experiments:
                    elements += [
                        Spacer(0, 20),
                        *self.__build_brief(experiments),
                        Spacer(0, 20),
                        *self.__build_simple_table(experiments),
                    ]
                doc.build(elements, onFirstPage=self.__draw_images)
                logger.info(f"PDF report successfully created in {self.output_path} (simplified format)")
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

    def __build_header(self, type_: str) -> tuple:
        """
        Generates the header section for the repository analysis report.

        Args:
            type_ (str): Type of validation (e.g., "Code", "Doc", "Paper").

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
        title_line1 = Paragraph(f"{type_} Validation Report", title_style)

        name = self.metadata.name
        if len(self.metadata.name) > 20:
            name = self.metadata.name[:20] + "..."

        title_line2 = Paragraph(
            f"for <a href='{self.repo_url}' color='#00008B'>{name}</a>",
            title_style,
        )

        return title_line1, title_line2

    @staticmethod
    def __build_brief(experiments: tuple[Experiment, ...]) -> tuple[Paragraph, Paragraph]:
        """
        Builds the first section of the report with correspondence and percentage metrics.

        Args:
            experiments: Assessed experiments used to compute aggregate correspondence.

        Returns:
            Paragraph elements for correspondence summary and experiment count.
        """
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            name="BriefNormal",
            parent=styles["Normal"],
            fontSize=12,
            leading=16,
            alignment=0,
            fontName=_unicode_font_name,
        )
        correspondence_sum = sum(e.correspondence_percent or 0.0 for e in experiments)
        percentages = int(correspondence_sum / len(experiments) * 100) if experiments else 0
        formula = "C = (Σ p<sub>i</sub> / n) × 100" f" = ({correspondence_sum:.2f} / {len(experiments)}) × 100"
        percentages_text = Paragraph(
            f"<b>Correspondence percentages: {percentages}%</b> " f"(<i>{formula}</i>)",
            normal_style,
        )
        num_experiments = Paragraph(f"<b>Number of experiments found: {len(experiments)}</b>", normal_style)
        return percentages_text, num_experiments

    @staticmethod
    def __build_conclusion(conclusion: str) -> tuple:
        """
        Builds the conclusion section of the report.

        Args:
            conclusion (str): Conclusion text for the report.

        Returns:
            list[Flowable]: Flowable elements for the section.
        """
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            name="ConclusionNormal",
            parent=styles["Normal"],
            fontSize=12,
            leading=16,
            alignment=0,
            fontName=_unicode_font_name,
        )
        conclusion_header = Paragraph("<b>Conclusion:</b>", normal_style)
        conclusion_text = Paragraph(
            conclusion,
            normal_style,
        )
        return Spacer(0, 10), conclusion_header, Spacer(0, 5), conclusion_text

    @staticmethod
    def __build_vkr_section(vkr_report: dict | None) -> list:
        """Build PDF elements for the VKR section: general info, score, checks, code quality."""
        if not vkr_report:
            return []

        from osa_tool.operations.analysis.vkr_scoring.scoring_engine import REPO_TYPE_LABELS

        styles = getSampleStyleSheet()
        header_style = ParagraphStyle(
            name="VkrHeader",
            parent=styles["Normal"],
            fontSize=13,
            leading=18,
            spaceBefore=4,
            fontName=_unicode_font_name,
        )
        normal_style = ParagraphStyle(
            name="VkrNormal",
            parent=styles["Normal"],
            fontSize=11,
            leading=15,
            fontName=_unicode_font_name,
        )
        note_style = ParagraphStyle(
            name="VkrNote",
            parent=normal_style,
            fontSize=9,
            textColor=colors.HexColor("#555555"),
        )

        summary = vkr_report.get("summary", {})
        score = summary.get("score", 0)
        breakdown = summary.get("score_breakdown", {})
        repo_type = summary.get("repo_type", "unknown")
        type_label = REPO_TYPE_LABELS.get(repo_type, repo_type.replace("_", " ").title())
        analyzed_at = vkr_report.get("analyzed_at", "")
        score_color = _score_color(score)

        # General info
        elements: list = [Paragraph(f"Repository type: {_esc(type_label)}", normal_style)]
        if analyzed_at:
            elements.append(Paragraph(f"Analyzed at: {_esc(analyzed_at)}", normal_style))
        elements.append(Spacer(0, 8))

        # Score
        elements.append(Paragraph("<b>Repository Quality Score</b>", header_style))
        score_style = ParagraphStyle(
            name="ScoreBig",
            parent=normal_style,
            fontSize=30,
            leading=34,
            textColor=colors.HexColor(score_color),
        )
        elements.append(Paragraph(f"{score}<font size=14 color='#888888'> / 100</font>", score_style))
        elements.append(Spacer(0, 8))

        # Repository checks (skip keys the score doesn't weight for this repo_type at all,
        # as well as ones explicitly marked non-applicable)
        applicable = [
            (key, label)
            for key, label in _CHECK_LABELS.items()
            if key in breakdown and breakdown[key].get("applicable") is not False
        ]
        if applicable:
            elements.append(Paragraph("<b>Repository Checks</b>", header_style))
            table_data = [
                [
                    Paragraph("<b>Check</b>", normal_style),
                    Paragraph("<b>Status</b>", normal_style),
                    Paragraph("<b>Points</b>", normal_style),
                ]
            ]
            for key, label in applicable:
                bd = breakdown.get(key, {})
                passed = bd.get("passed", False)
                earned = bd.get("earned", 0)
                weight = bd.get("weight", 0)
                status_style = ParagraphStyle(
                    name=f"VkrStatus_{key}",
                    parent=normal_style,
                    textColor=colors.HexColor("#27ae60" if passed else "#e74c3c"),
                )
                table_data.append(
                    [
                        Paragraph(_esc(label), normal_style),
                        Paragraph(f"<b>{'PASS' if passed else 'FAIL'}</b>", status_style),
                        Paragraph(f"{earned} / {weight}", normal_style),
                    ]
                )

            table = Table(table_data, colWidths=[220, 100, 100])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C0C8D0")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (1, 0), (2, -1), "CENTER"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            elements.append(table)
            elements.append(Spacer(0, 8))

        # Code quality
        syntax = summary.get("syntax", {})
        docstrings = summary.get("docstrings", {})
        elements.append(Paragraph("<b>Code Quality</b>", header_style))

        ok = syntax.get("ok")
        if ok is True:
            elements.append(Paragraph(f"<b>Syntax:</b> OK — {_esc(syntax.get('summary', ''))}", normal_style))
        elif ok is False:
            elements.append(Paragraph(f"<b>Syntax:</b> Errors — {_esc(syntax.get('summary', ''))}", normal_style))
            for err in syntax.get("errors", [])[:5]:
                elements.append(Paragraph(f"• {_esc(err)}", note_style))
        else:
            elements.append(Paragraph(f"<b>Syntax:</b> {_esc(syntax.get('summary', 'unavailable'))}", normal_style))

        coverage_pct = docstrings.get("coverage_pct")
        if coverage_pct is not None:
            elements.append(Paragraph(f"<b>Docstring coverage:</b> {coverage_pct}%", normal_style))
        else:
            elements.append(
                Paragraph(f"<b>Docstrings:</b> {_esc(docstrings.get('summary', 'unavailable'))}", normal_style)
            )

        return elements

    @staticmethod
    def __build_claims_section(claims_analysis: dict | None) -> list:
        """Build PDF elements for the claims verification section (paper/doc claims vs. code)."""
        if not claims_analysis:
            return []

        styles = getSampleStyleSheet()
        header_style = ParagraphStyle(
            name="ClaimsHeader",
            parent=styles["Normal"],
            fontSize=13,
            leading=18,
            spaceBefore=4,
            fontName=_unicode_font_name,
        )
        normal_style = ParagraphStyle(
            name="ClaimsNormal",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            fontName=_unicode_font_name,
        )
        note_style = ParagraphStyle(
            name="ClaimsNote",
            parent=normal_style,
            textColor=colors.HexColor("#555555"),
        )

        stats = claims_analysis.get("stats", {})
        total = stats.get("total", 0)
        implemented = stats.get("implemented", 0)
        rate_pct = stats.get("implementation_rate_pct", 0)
        rate_color = _score_color(rate_pct)

        elements: list = [
            Paragraph("<b>Claims Analysis</b>", header_style),
            Spacer(0, 4),
            Paragraph(f"Total claims: <b>{total}</b>", normal_style),
            Paragraph(f"Implemented: <b>{implemented} / {total}</b>", normal_style),
            Paragraph(
                f"Verifiability of statements score: <font color='{rate_color}'><b>{rate_pct}%</b></font>",
                normal_style,
            ),
            Spacer(0, 8),
        ]

        claims = claims_analysis.get("claims", [])
        if not claims:
            elements.append(Paragraph("No claims were extracted.", normal_style))
            return elements

        table_data = [
            [
                Paragraph("<b>Claim</b>", normal_style),
                Paragraph("<b>Status</b>", normal_style),
                Paragraph("<b>Confidence</b>", normal_style),
                Paragraph("<b>Section</b>", normal_style),
            ]
        ]
        for claim in claims:
            impl = claim.get("implementation", {})
            done = impl.get("implemented", False)
            status_style = ParagraphStyle(
                name="ClaimStatus",
                parent=normal_style,
                textColor=colors.HexColor("#27ae60" if done else "#e74c3c"),
            )

            claim_cell = _esc(claim.get("claim", ""))
            explanation = impl.get("explanation", "")
            if explanation:
                claim_cell += f"<br/><font color='#555555'>{_esc(explanation)}</font>"

            confidence_cell = _esc(impl.get("confidence", ""))
            evidence = impl.get("evidence_file") or ""
            if evidence:
                confidence_cell += f"<br/><font color='#555555'>{_esc(evidence)}</font>"

            table_data.append(
                [
                    Paragraph(claim_cell, normal_style),
                    Paragraph(f"<b>{'PASS' if done else 'FAIL'}</b>", status_style),
                    Paragraph(confidence_cell, normal_style),
                    Paragraph(_esc(claim.get("section_name", "")), note_style),
                ]
            )

        table = Table(table_data, colWidths=[230, 55, 90, 95], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C0C8D0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elements.append(table)
        return elements

    def __build_simple_table(self, experiments) -> tuple:
        """Simplified table format without RoundedCard for large content."""
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            name="SimpleNormal",
            parent=styles["Normal"],
            fontSize=10,
            leading=12,
            alignment=0,
            fontName=_unicode_font_name,
        )
        elements = []
        for i, experiment in enumerate(experiments, 1):
            if i > 1:
                elements.append(Spacer(0, 12))
            elements.append(Paragraph(f"<b>Experiment {i}</b>", normal_style))
            elements.append(
                Paragraph(
                    f"<i>Correspondence: {(experiment.correspondence_percent or 0.0) * 100:.1f}%</i>", normal_style
                )
            )
            elements.append(Spacer(0, 4))
            elements.append(Paragraph(f"<b>Description:</b> {experiment.description_from_paper[:300]}", normal_style))
            if experiment.impl_src_path:
                elements.append(Paragraph(f"<b>Found in:</b> {'; '.join(experiment.impl_src_path[:2])}", normal_style))
        return tuple(elements)

    def __build_table(self, experiments) -> tuple:
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            name="TableNormal",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            alignment=0,
            fontName=_unicode_font_name,
        )
        bullet_style = ParagraphStyle(
            name="TableBullet",
            parent=normal_style,
            leftIndent=8,
            fontName=_unicode_font_name,
        )

        cards = []
        for i, experiment in enumerate(experiments, 1):
            if i > 1:
                cards.append(PageBreak())
            card_content = []
            header_row = Table(
                [
                    [
                        Paragraph(f"<b>Experiment {i}</b>", normal_style),
                        Paragraph(
                            f"<b>Correspondence:</b> {(experiment.correspondence_percent or 0.0) * 100:.1f}%",
                            normal_style,
                        ),
                    ]
                ],
                colWidths=[180, 180],
            )
            header_row.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (0, 0), "LEFT"),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.HexColor("#D5DCE3")),
                    ]
                )
            )
            card_content.append(header_row)
            card_content.append(
                Paragraph(
                    f"<b>Formulation stated:</b> {experiment.description_from_paper}",
                    normal_style,
                )
            )
            card_content.append(Paragraph("<b>Implementation found:</b>", normal_style))

            if experiment.impl_src_path:
                for impl in experiment.impl_src_path:
                    card_content.append(Paragraph(f"• {impl}", bullet_style))
            else:
                card_content.append(Paragraph("• None", bullet_style))

            reasoning = experiment.reasoning
            if reasoning != "":
                card_content.append(Paragraph(f"<b>Reasoning:</b> {reasoning}", normal_style))

            card_content.append(Paragraph("<b>Missing components:</b>", normal_style))
            if experiment.missing:
                for missing in experiment.missing:
                    card_content.append(Paragraph(f"• {missing}", bullet_style))
            else:
                card_content.append(Paragraph("• None", bullet_style))

            cards.append(RoundedCard(card_content, width=420, padding=6))
            cards.append(Spacer(0, 8))

        return tuple(cards)
