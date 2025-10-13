from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.context.article_content import PdfParser
from osa_tool.readmegen.context.article_path import get_pdf_path
from osa_tool.utils import logger
from osa_tool.validation.code_analyzer import CodeAnalyzer

article_extract = """
INPUT DATA:
{pdf_content}

TASK:
Analyze the attached scientific paper and extract the following sections as plain text:

1. The **Abstract** section (usually titled "Abstract").
2. The section describing the **experiments** (may be titled "Experiments", "Experimental Setup", "Methodology", "Materials and Methods", or similar—use your best judgment to identify where the experimental procedures are described).
3. The **Results** section (typically titled "Results", "Findings", or similar—do not include the "Discussion" or "Conclusion" unless they are merged with Results).

Return the extracted text for each section in a JSON object with the keys: "abstract", "experiments", and "results".

RULES:
- Return ONLY a valid JSON object—no additional text, explanations, or formatting.
- For each section:
  - If found, include the full text exactly as it appears (preserving line breaks, equations, BibTeX, DOIs, etc.).
  - If multiple relevant sections exist (e.g., multiple experiment subsections), concatenate them into a single string in logical order.
  - If no such section exists, return an empty string ("").
- Do NOT paraphrase, summarize, or add content.
- Do NOT include section titles unless they appear in the original text.

OUTPUT FORMAT:
Return a valid JSON object with the following structure:

{{
  "abstract": "string",
  "experiments": "string",
  "results": "string"
}}
"""

validate_paper_against_repo = """
INPUT DATA:
{paper_info}

{code_files_info}

TASK:
Compare the scientific paper's described experiments and results with the actual implementation and experimental code in the repository.

Specifically:
- Does the code implement the methods, models, or algorithms described in the paper's experiments section?
- Are the datasets, evaluation metrics, and experimental procedures consistent with those reported?
- Are the results (e.g., numerical outcomes, figures, tables) reproducible from the provided code?

Based on this comparison:
1. Determine if there is substantial compliance between the paper and the code (`true` for compliant, `false` otherwise).
2. Assign a percentage score (0.0 to 100.0) reflecting how well the repository code aligns with the paper’s experimental claims.
3. Provide a concise justification for your assessment.

RULES:
- Return ONLY a valid JSON object—no additional text, markdown, or explanations.
- The percentage must be a float between 0.0 and 100.0.
- If key experimental details are missing from the code (e.g., no training script, no evaluation), reflect this in a low score.
- Base your judgment solely on the provided paper excerpts and code analysis.

OUTPUT FORMAT:
{{
  "correspondence": bool,
  "percentage": float,
  "conclusion": str
}}
"""


class PaperValidator:
    def __init__(self, config_loader: ConfigLoader):
        self.code_analyzer = CodeAnalyzer(config_loader)
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)

    def validate(self, article:str) -> None:
        try:
            paper_info = self.process_paper(article)
            code_files = self.code_analyzer.get_code_files()
            code_files_info = self.code_analyzer.process_code_files(code_files)
            result = self.validate_paper_against_repo(paper_info, code_files_info)
            logger.info(result)
        except Exception as e:
            logger.error(f"Error while validating paper against repo: {e}")

    def process_paper(self, article: str):
        logger.info("Loading PDF...")
        path_to_pdf = get_pdf_path(article)
        if not path_to_pdf:
            raise ValueError(f"Invalid PDF source provided: {path_to_pdf}. Could not locate a valid PDF.")
        logger.info("Extracting text from PDF ...")
        pdf_content = PdfParser(path_to_pdf).data_extractor()
        logger.info("Sending request to extract sections ...")
        response = self.model_handler.send_request(article_extract.format(pdf_content=pdf_content))
        logger.debug(response)
        return response

    def validate_paper_against_repo(self, paper_info, code_files_info):
        logger.info("Validating paper against repository ...")
        response = self.model_handler.send_request(
            validate_paper_against_repo.format(paper_info=paper_info, code_files_info=code_files_info)
        )
        logger.debug(response)
        return response
