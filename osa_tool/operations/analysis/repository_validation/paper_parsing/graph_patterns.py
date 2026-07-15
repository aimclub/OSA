import re
from typing import List, Tuple, Dict


# Each tuple: (target_category, compiled_regex)
# The regex captures the reference number so we can match "Fig. 1" → figure #1.
_REF_PATTERNS: List[Tuple[str, re.Pattern]] = [
    # Figures: Fig. 1, Figure 1, fig.1, Рис. 1, Рисунок 1
    (
        "figure",
        re.compile(
            r"(?:fig(?:ure)?|рис(?:ун(?:ок|ке|ка))?)\s*\.?\s*(\d+)",
            re.IGNORECASE,
        ),
    ),
    # Tables: Table 1, Tab. 1, Табл. 1, Таблица 1
    (
        "table",
        re.compile(
            r"(?:tab(?:le)?|табл(?:иц[аеыу])?)\s*\.?\s*(\d+)",
            re.IGNORECASE,
        ),
    ),
    # Formulas / Equations: Eq. 1, Equation (1), Formula 1, Формула 1
    (
        "formula",
        re.compile(
            r"(?:eq(?:uation)?|formula|формул[аеыу]?)\s*\.?\s*[(\[]?\s*(\d+)\s*[)\]]?",
            re.IGNORECASE,
        ),
    ),
]

# Map element type names (from YOLO classes) → reference category
_ELEM_TYPE_TO_CATEGORY: Dict[str, str] = {
    "figure": "figure",
    "figure_caption": "figure",
    "table": "table",
    "table_caption": "table",
    "table_footnote": "table",
    "isolate_formula": "formula",
    "formula_caption": "formula",
}

# Element types considered "caption-like"
_CAPTION_TYPES = {"figure_caption", "table_caption", "formula_caption"}

# Element types that captions attach to
_CAPTIONABLE_TYPES = {"figure", "table", "isolate_formula"}

# Types treated as headers / titles
_HEADER_TYPES = {"title"}

# Types treated as body paragraphs
_PARAGRAPH_TYPES = {"plain text"}

# Content types that can belong to a title's section (everything that is not a
# title and carries document content: paragraphs, figures, tables, formulas and
# their captions / footnotes).
_SECTION_MEMBER_TYPES = _PARAGRAPH_TYPES | _CAPTIONABLE_TYPES | _CAPTION_TYPES | {"table_footnote"}
