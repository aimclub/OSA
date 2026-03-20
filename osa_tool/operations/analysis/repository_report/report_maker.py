import os
from abc import ABC, abstractmethod
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
    Flowable,
)

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.operations.analysis.repository_report.report_generator import TextGenerator, AfterReportTextGenerator
from osa_tool.scheduler.plan import Plan
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root


class AbstractReportGenerator(ABC):
    """
    Abstract base class for generating repository analysis reports in PDF format.
    
        This class provides a framework for creating structured PDF reports that include
        repository metadata, statistics, and analysis results. It handles common
        components such as headers, tables, QR codes, and basic layout, while allowing
        subclasses to define specific content sections.
    
        Attributes:
            sourcerank (SourceRank): Tool for calculating source code ranking metrics.
            git_agent (GitAgent): Git operations handler.
            metadata (any): Repository metadata extracted from git_agent.
            repo_url (str): URL of the target Git repository.
            osa_url (str): Static URL for the OSA project.
            logo_path (str): Filesystem path to the OSA logo image.
            filename (str): Generated filename for the output PDF report.
            output_path (str): Full filesystem path where the report will be saved.
            start_log (str): Log message indicating the start of repository analysis.
            report_header (str): Title used in the generated report.
    
        Methods:
            __init__: Initializes the report generator with configuration and Git data.
            table_builder: Creates styled tables with configurable column widths and optional row coloring.
            generate_qr_code: Creates a QR code image for the repository URL.
            draw_images_and_tables: Draws images, QR codes, lines, and tables onto the PDF canvas.
            header: Generates the header section of the report.
            table_generator: Produces tables for repository statistics and key element presence.
            body_first_part: Creates the initial body content with repository details as a bulleted list.
            get_styles: Defines custom paragraph styles for document formatting.
            body_second_part: Abstract method for subclasses to define specific additional content.
            build_pdf: Orchestrates the creation and assembly of the complete PDF document.
    """

    def __init__(self, config_manager: ConfigManager, git_agent: GitAgent):
        """
        Initializes the AbstractReportGenerator instance.
        
        This constructor sets up the necessary components for generating a repository analysis report, including configuration, Git metadata, and output file paths. It prepares the instance with tools for source ranking, metadata extraction, and defines the paths and names for the final PDF report.
        
        Args:
            config_manager: Manages configuration settings, including the Git repository URL.
            git_agent: Handles Git operations and provides repository metadata.
        
        Initializes the following instance attributes:
            sourcerank (SourceRank): Tool for calculating source code ranking metrics, initialized with the provided config_manager.
            git_agent (GitAgent): The provided Git operations handler.
            metadata (any): Repository metadata (e.g., name, full_name) extracted from the git_agent's metadata attribute.
            repo_url (str): URL of the target Git repository, obtained from the configuration's git settings.
            osa_url (str): Static URL for the OSA project ("https://github.com/aimclub/OSA").
            logo_path (str): Filesystem path to the OSA logo image, constructed relative to the osa_tool project root.
            filename (str): Generated filename for the output PDF report, using the repository name from metadata (format: "{name}_report.pdf").
            output_path (str): Full filesystem path where the report PDF will be saved, set to the current working directory combined with the filename.
            start_log (str): Log message indicating the start of repository analysis, includes the repository's full name.
            report_header (str): Title used in the generated report ("Repository Analysis Report").
        """
        self.sourcerank = SourceRank(config_manager)
        self.git_agent = git_agent
        self.metadata = self.git_agent.metadata
        self.repo_url = config_manager.get_git_settings().repository
        self.osa_url = "https://github.com/aimclub/OSA"

        self.logo_path = os.path.join(osa_project_root(), "docs", "images", "osa_logo.PNG")

        self.filename = f"{self.metadata.name}_report.pdf"
        self.output_path = os.path.join(os.getcwd(), self.filename)
        self.start_log = f"Starting analysis for repository {self.metadata.full_name}"
        self.report_header = "Repository Analysis Report"

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
            data: The table data, where the first row is treated as a header.
            w_first_col: The width of the first column.
            w_second_col: The width of the second column.
            coloring: If True, applies conditional row coloring based on the values in the second column. Defaults to False.
        
        Returns:
            A formatted table with applied styles.
        
        Notes:
            - The table is styled with a light grey header row, a default pink background for data rows, and a black grid.
            - The first column is left-aligned, and the second column is center-aligned.
            - When `coloring` is True, rows are colored based on the value in the second column: light green for "✓" and light coral otherwise.
            - This is a static method, meaning it can be called without an instance of the class.
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
                style.append(("BACKGROUND", (1, row_idx), (1, row_idx), bg_color))

        table.setStyle(TableStyle(style))
        return table

    def generate_qr_code(self) -> str:
        """
        Generates a QR code for the OSA URL and saves it as a temporary image file.
        The QR code is created from the `osa_url` instance attribute, which is the URL to be encoded.
        This is used to embed a scannable link in generated reports or documentation for quick access.
        
        Returns:
            str: The file path of the generated QR code image (saved as "temp_qr.png" in the current working directory).
        """
        qr = qrcode.make(self.osa_url)
        qr_path = os.path.join(os.getcwd(), "temp_qr.png")
        qr.save(qr_path)
        return qr_path

    def draw_images_and_tables(self, canvas_obj: Canvas, doc: SimpleDocTemplate) -> None:
        """
        Draws images, a QR code, lines, and tables on the given PDF canvas.
        Specifically, it places the OSA logo and a generated QR code (both linked to the OSA URL), draws two horizontal lines as separators, and renders two tables generated by the class's table_generator method. The QR code file is created temporarily and deleted after drawing.
        
        Args:
            canvas_obj (Canvas): The PDF canvas object to draw on.
            doc (SimpleDocTemplate): The PDF document that is being generated. This parameter is not used directly but is required by the ReportLab framework for page rendering.
        
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
        
        The header consists of two lines: the first displays the report's main title (self.report_header), and the second line shows the repository name, truncated if longer than 20 characters, as a clickable hyperlink to the repository URL. This provides immediate identification of the report's subject and allows quick navigation to the repository.
        
        Args:
            self: The AbstractReportGenerator instance containing report metadata and configuration.
        
        Returns:
            list: A list of two Paragraph elements (from the reportlab library) representing the header content. The first Paragraph is the report title, and the second is the linked repository name.
        """
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
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
            f"for <a href='{self.repo_url}' color='#00008B'>{name}</a>",
            title_style,
        )

        elements = [title_line1, title_line2]
        return elements

    def table_generator(self) -> tuple[Table, Table]:
        """
        Generates two tables containing repository statistics and presence of key elements.
        
        The first table includes basic repository statistics (stars, forks, open issues), and the second table shows the presence of important repository elements such as README, License, Documentation, etc. This method is used to create visual summaries for reports, helping to quickly assess repository health and completeness.
        
        Args:
            self: The instance of AbstractReportGenerator.
        
        Returns:
            tuple[Table, Table]: A tuple containing two Table objects. The first table presents repository statistics, and the second table indicates the presence of key repository elements.
        """
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            name="LeftAlignedNormal",
            parent=styles["Normal"],
            fontSize=12,
            alignment=1,
        )
        data1 = [
            [
                Paragraph("<b>Statistics</b>", normal_style),
                Paragraph("<b>Values</b>", normal_style),
            ],
            ["Stars Count", str(self.metadata.stars_count)],
            ["Forks Count", str(self.metadata.forks_count)],
            ["Issues Count", str(self.metadata.open_issues_count)],
        ]
        data2 = [
            [
                Paragraph("<b>Metric</b>", normal_style),
                Paragraph("<b>Values</b>", normal_style),
            ],
            ["README Presence", "✓" if self.sourcerank.readme_presence() else "✗"],
            ["License Presence", "✓" if self.sourcerank.license_presence() else "✗"],
            ["Documentation Presence", "✓" if self.sourcerank.docs_presence() else "✗"],
            ["Examples Presence", "✓" if self.sourcerank.examples_presence() else "✗"],
            ["Requirements Presence", "✓" if self.sourcerank.requirements_presence() else "✗"],
            ["Tests Presence", "✓" if self.sourcerank.tests_presence() else "✗"],
            ["Description Presence", "✓" if self.metadata.description else "✗"],
        ]
        table1 = self.table_builder(data1, 120, 76)
        table2 = self.table_builder(data2, 160, 76, True)
        return table1, table2

    def body_first_part(self) -> ListFlowable:
        """
        Generates the first part of the body content for the repository report.
        
        This includes the repository name with a hyperlink, owner information with a hyperlink,
        and the repository creation date. The data is presented as a bulleted list.
        
        The repository name is truncated with an ellipsis if it exceeds 16 characters to maintain
        consistent formatting in the report. The creation date is reformatted from ISO 8601 to a
        more readable local date-time format.
        
        Returns:
            ListFlowable: A ListFlowable object containing a bulleted list of repository details.
            The list items are formatted as left-aligned paragraphs with specific styling.
        """
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
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
            f"Repository Name: <a href='{self.repo_url}' color='#00008B'>{name}</a>",
            normal_style,
        )
        owner_link = Paragraph(
            f"Owner: <a href='{self.metadata.owner_url}' color='#00008B'>{self.metadata.owner}</a>",
            normal_style,
        )
        created_at = Paragraph(
            f"Created at: {datetime.strptime(self.metadata.created_at, '%Y-%m-%dT%H:%M:%SZ').strftime('%d.%m.%Y %H:%M')}",
            normal_style,
        )

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
        """
        Generates and returns custom paragraph styles for document formatting.
        
        This static method creates two predefined `ParagraphStyle` objects for consistent
        styling within generated documents. The styles are built using the reportlab
        library's sample style sheet as a foundation.
        
        Returns:
            tuple[ParagraphStyle, ParagraphStyle]: A tuple containing two paragraph styles:
                - 'LeftAlignedNormal': A base style derived from the 'Normal' sample style,
                  with specific formatting adjustments including a 12pt font size, 13pt leading,
                  and 20-unit negative indents on both left and right sides to create a
                  full-width, left-aligned paragraph appearance.
                - 'CustomStyle': A style that inherits from 'LeftAlignedNormal' and adds
                  additional vertical spacing (6 units before and 2 units after the paragraph)
                  for use as a spaced paragraph variant.
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
        return normal_style, custom_style

    @abstractmethod
    def body_second_part(self) -> list[Flowable]:
        """
        Generates the second part of the document body.
        
        This is an abstract method that must be implemented by subclasses to define the specific layout or content for the latter portion of the generated document. This separation allows for modular document construction, enabling subclasses to structure complex reports in distinct, manageable sections.
        
        Returns:
            A list of ReportLab Flowable objects to be rendered in the document. These objects represent the visual components (such as paragraphs, tables, or images) that will appear in the second part of the document body.
        """
        pass

    def build_pdf(self) -> None:
        """
        Generates and builds the PDF report for the repository analysis.
        
        This method initializes the PDF document, adds the header, body content (first and second parts),
        and then generates the PDF file. The `draw_images_and_tables` method is used to draw images and tables
        on the first page of the document.
        
        WHY: The method orchestrates the PDF creation by assembling predefined report sections (header, body parts)
        with specific spacing and applies a custom drawing function to the first page for visual elements like images and tables.
        
        Args:
            self: The report generator instance containing the report data and configuration.
        
        Returns:
            None
        
        Raises:
            Exception: If there is an error during the PDF creation process, such as file I/O issues or problems with the document layout.
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
                    Spacer(0, 110),
                    *self.body_second_part(),
                ],
                onFirstPage=self.draw_images_and_tables,
            )
            logger.info(f"PDF report successfully created in {self.output_path}")
        except Exception as e:
            logger.error("Error while building PDF report, %s", e, exc_info=True)


class ReportGenerator(AbstractReportGenerator):
    """
    Generates a comprehensive PDF report for a given open-source repository.
    
        This class orchestrates the process of analyzing a repository, generating descriptive text, and compiling the findings into a PDF document. It can optionally handle the upload of the generated report to a remote git repository.
    
        Attributes:
            text_generator: An instance of TextGenerator used for creating the narrative content of the report.
            create_fork: A boolean flag indicating whether a repository fork should be created for upload operations.
            events: A list used to track and store OperationEvent instances during the report generation lifecycle.
    
        Methods:
            __init__: Initializes the generator with configuration, git handling capabilities, and fork preferences.
            run: Executes the full report generation and optional upload process, returning the result and event log.
            body_second_part: Creates the analysis section of the report for PDF inclusion.
    """


    def __init__(self, config_manager: ConfigManager, git_agent: GitAgent, create_fork: bool):
        """
        Initializes a new instance of the ReportGenerator with configuration, git handling, and fork preferences.
        
        Args:
            config_manager: The manager responsible for handling application configuration.
            git_agent: The agent used for performing git operations.
            create_fork: A boolean flag indicating whether a repository fork should be created. If True, operations that modify the repository will target a fork to preserve the original.
        
        Attributes:
            text_generator: An instance of TextGenerator used for content creation, initialized with the config manager and the instance's metadata.
            create_fork: Stores the preference for whether to fork the repository.
            events: A list used to track and store OperationEvent instances during the lifecycle of the object, enabling logging and monitoring of operations.
        """
        super().__init__(config_manager, git_agent)
        self.text_generator = TextGenerator(config_manager, self.metadata)
        self.create_fork = create_fork
        self.events: list[OperationEvent] = []

    def run(self) -> dict:
        """
        Executes the report generation process, including PDF building and optional remote upload.
                
        This method orchestrates the creation of a PDF report, logs the generation event, and, if configured, utilizes a git agent to upload the resulting file to a repository. It captures and returns the outcome of these operations along with a history of events occurred during execution. The method ensures that any errors during PDF generation are caught and logged as failure events, maintaining a complete audit trail.
        
        Args:
            self: The instance of the class. The method relies on instance attributes such as `filename`, `output_path`, `create_fork`, `git_agent`, and `events` to control the process and track outcomes.
        
        Returns:
            dict: A dictionary containing two keys:
                - 'result': A dictionary itself, which contains either the key 'report' with the generated report's filename on success, or the key 'error' with an error message string on failure.
                - 'events': A list of OperationEvent objects recorded during the process, documenting key steps like generation, upload, or failure.
        """
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
        Generates the second part of the report, which contains the detailed analysis of the repository.
        This section compiles structured findings from the automated analysis into formatted paragraphs for inclusion in the PDF.
        
        Args:
            None
        
        Returns:
            A list of Flowable objects (Paragraphs) representing the report's second part.
            The content includes:
                - Repository Structure: compliance, missing files, and organization.
                - README Analysis: overall quality and individual field assessments.
                - Documentation: presence of tests, documentation quality, and outdated content.
                - Key Shortcomings: any identified critical issues.
                - Recommendations: suggested improvements for the repository.
        """

        parsed_report = self.text_generator.make_request()
        normal_style, custom_style = self.get_styles()
        story = []

        # Repository Structure
        story.append(Paragraph("<b>Repository Structure:</b>", custom_style))
        story.append(Paragraph(f"• Compliance: {parsed_report.structure.compliance}", normal_style))
        if parsed_report.structure.missing_files:
            missing_files = ", ".join(parsed_report.structure.missing_files)
            story.append(Paragraph(f"• Missing files: {missing_files}", normal_style))
        story.append(Paragraph(f"• Organization: {parsed_report.structure.organization}", normal_style))

        # README Analysis
        story.append(Paragraph("<b>README Analysis:</b>", custom_style))
        story.append(Paragraph(f"• Quality: {parsed_report.readme.readme_quality}", normal_style))

        for field_name, value in parsed_report.readme.model_dump().items():
            if field_name == "readme_quality":
                continue

            story.append(
                Paragraph(
                    f"• {field_name.replace('_', ' ').capitalize()}: {value.value}",
                    normal_style,
                )
            )

        # Documentation
        story.append(Paragraph("<b>Documentation:</b>", custom_style))
        story.append(
            Paragraph(
                f"• Tests present: {parsed_report.documentation.tests_present.value}",
                normal_style,
            )
        )
        story.append(
            Paragraph(
                f"• Documentation quality: {parsed_report.documentation.docs_quality}",
                normal_style,
            )
        )
        story.append(
            Paragraph(
                f"• Outdated content: {'Yes' if parsed_report.documentation.outdated_content else 'No'}",
                normal_style,
            )
        )

        if parsed_report.assessment.key_shortcomings:
            story.append(Paragraph("<b>Key Shortcomings:</b>", custom_style))
            for shortcoming in parsed_report.assessment.key_shortcomings:
                story.append(Paragraph(f"  - {shortcoming}", normal_style))

        # Recommendations
        story.append(Paragraph("<b>Recommendations:</b>", custom_style))
        for rec in parsed_report.assessment.recommendations:
            story.append(Paragraph(f"  - {rec}", normal_style))

        return story


class WhatHasBeenDoneReportGenerator(AbstractReportGenerator):
    """
    Generates a comprehensive PDF report summarizing completed tasks and improvements made to a repository.
    
        This class orchestrates the creation of a structured work summary document by:
        1. Extracting task information and results from provided plans
        2. Generating descriptive text content for the report
        3. Assembling the content into a formatted PDF document
        4. Tracking operational events throughout the report generation process
    
        Attributes:
            filename: The name of the generated PDF report file based on metadata
            create_fork: Stores whether a fork should be created during the process
            output_path: The absolute path where the summary report will be saved
            completed_tasks: A list of tasks extracted from the plan for reporting
            task_results: A dictionary containing the results of the executed tasks
            text_generator: An instance of AfterReportTextGenerator used to create report content
            start_log: A string message indicating the start of the summary creation process
            report_header: The title header used within the summary report
            events: A list to store operation events occurring during the process
    
        Methods:
            __init__: Initializes the report generator with configuration, git tools, and task plans
            run: Builds the complete PDF report and returns structured results with tracked events
            body_second_part: Generates the improvement steps section of the report for PDF assembly
    """


    def __init__(
        self,
        config_manager: ConfigManager,
        git_agent: GitAgent,
        create_fork: bool,
        plan: Plan,
    ):
        """
        Initialize the work summary generator with configuration, git tools, and task plans.
        
        Args:
            config_manager: The manager responsible for handling configuration settings.
            git_agent: The agent used for performing Git-related operations.
            create_fork: A boolean flag indicating whether a fork should be created.
            plan: The plan object containing tasks and results to be reported.
        
        Attributes:
            filename: The name of the generated PDF report file based on metadata.
            create_fork: Stores whether a fork should be created during the process.
            output_path: The absolute path where the summary report will be saved.
            completed_tasks: A list of tasks extracted from the plan for reporting.
            task_results: A dictionary containing the results of the executed tasks.
            text_generator: An instance of AfterReportTextGenerator used to create report content.
            start_log: A string message indicating the start of the summary creation process.
            report_header: The title header used within the summary report.
            events: A list to store operation events occurring during the process.
        
        Why:
            This initializer sets up the generator by extracting relevant data from the plan (tasks and results) and preparing the necessary components to produce a summary report. The filename and output path are constructed automatically to standardize report generation. The create_fork flag is preserved for later use in the workflow, and events are initialized to log operations during report creation.
        """
        super().__init__(config_manager, git_agent)
        self.filename = f"{self.metadata.name}_work_summary.pdf"
        self.create_fork = create_fork
        self.output_path = os.path.join(os.getcwd(), self.filename)
        self.completed_tasks = plan.list_for_report
        self.task_results = plan.results or {}
        self.text_generator = AfterReportTextGenerator(config_manager, self.completed_tasks, self.task_results)
        self.start_log = f"Starting creating summary for OSA work"
        self.report_header = "OSA Work Summary"
        self.events: list[OperationEvent] = []

    def run(self) -> dict:
        """
        Build the OSA work summary PDF and return a structured result with events.
        
        This method orchestrates the PDF generation process, handles optional file uploads, and tracks each step as an OperationEvent. It follows a consistent contract used by other operations in the system, ensuring callers always receive a dict with "result" and "events" keys. This uniformity allows for standardized error handling and event logging across different report generators.
        
        Args:
            self: The WhatHasBeenDoneReportGenerator instance.
        
        Returns:
            A dictionary containing two keys:
                - "result": A dict with either the generated report filename under the key "report" or, in case of failure, an error description under the key "error".
                - "events": A list of OperationEvent objects recorded during execution. Events track generation, optional upload, and any failure.
        
        The method attempts the following steps in order:
            1. Calls `build_pdf()` to create the PDF file.
            2. Appends a GENERATED event upon successful PDF creation.
            3. If `create_fork` is True and the output file exists, uploads the report via `git_agent.upload_report()` and appends an UPLOADED event.
            4. Returns a success result with the filename and all recorded events.
        
        If a `ValueError` is raised during any step, the method catches it, appends a FAILED event with error details, and returns a result containing the error message alongside the events.
        """
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
        Generates the second part of the report, which contains the steps for improving the repository taken by the OSA.
        
        This section details the actions performed by the OSA tool, including a summary of overall improvements and a task-by-task breakdown. It structures the content for inclusion in the PDF report.
        
        Args:
            None
        
        Returns:
            list: A list of Flowable objects (primarily Paragraph instances) representing the formatted content for the PDF report. The list includes:
                - A header titled "What has been done:".
                - A summary paragraph of the overall improvements.
                - A header titled "Report by tasks:".
                - For each block of tasks:
                    - A sub-header with the block name.
                    - A description of the block.
                    - A bulleted list of individual tasks within the block, each marked as "Yes" or "No" to indicate completion status.
        """
        response = self.text_generator.make_request()
        normal_style, custom_style = self.get_styles()
        story = []
        story.append(Paragraph("<b>What has been done:</b>", custom_style))
        story.append(Paragraph(response.summary, normal_style))
        story.append(Paragraph("<b>Report by tasks:</b>", custom_style))
        for block in response.blocks:
            story.append(Paragraph(f"<b>{block.name}</b>", custom_style))
            story.append(Paragraph(block.description, normal_style))
            for task, was_do in block.tasks:
                task_result = "Yes" if was_do else "No"
                story.append(
                    Paragraph(
                        f"• {task}: {task_result}",
                        normal_style,
                    )
                )
        return story
