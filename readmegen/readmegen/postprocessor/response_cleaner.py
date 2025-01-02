"""Utility functions cleaning and formatting LLM API responses."""

import re


def process_markdown(text):
    """Remove uneven Markdown syntax while preserving valid formatting."""
    # Remove extra asterisks at the end of lines
    text = re.sub(r"\*+$", "", text, flags=re.MULTILINE)

    # Remove unmatched bullets or hyphens at the beginning of lines
    text = re.sub(r"^[\s]*[-*]\s+", "", text, flags=re.MULTILINE)

    # Preserve valid bold and italic formatting
    # This regex handles nested bold and italic formatting
    text = re.sub(
        r"\*{1,2}(?P<content>[^*\n]+(?:\*{1,2}[^*\n]+\*{1,2}[^*\n]+)*)\*{1,2}",
        lambda m: (
            m.group(0) if m.group(0).count("*") % 2 == 0 else m.group(0)[1:-1]
        ),
        text,
    )

    # Remove standalone asterisks or underscores
    text = re.sub(r"(?<!\*)\*(?!\*)|(?<!_)_(?!_)", "", text)

    return text.strip()


def process_text(text: str) -> str:
    """Format and clean generated text from the LLM."""
    # Remove all text before and including the first colon if any exist
    text = re.sub(r"^[^:]*:\s*", "", text)

    # Remove any text before and including "**:"
    text = re.sub(r"\*\*:\s*", "", text, flags=re.DOTALL)

    # Remove single and double quotes that are missing closing counterpart
    text = re.sub(r"['\"](.*?)$", r"\1", text)
    text = re.sub(r"^(.*?)['\"]", r"\1", text)

    # Remove specific pattern and rephrase
    text = re.sub(
        r"\*\*Code Summary:\*\*\s*(.*?)\s*provides functions to",
        r"Provides functions to",
        text,
        flags=re.DOTALL,
    )
    # Remove single and double quotes around any text
    text = re.sub(r"(?<!\w)['\"](.*?)['\"](?!\w)", r"\1", text)

    # Remove newlines and tabs
    text = text.replace("\n", "").replace("\t", "")

    # Remove non-letter characters from the beginning of the string
    text = re.sub(r"^[^a-zA-Z]*", "", text)

    # Remove extra white space around punctuation except for '('
    text = re.sub(r"\s*([)'.!,?;:])(?!\.\s*\w)", r"\1", text)

    # Remove extra white space before opening parentheses
    text = re.sub(r"(\()\s*", r"\1", text)

    # Replace multiple consecutive spaces with a single space
    text = re.sub(r" +", " ", text)

    # Remove extra white space around hyphens
    text = re.sub(r"\s*-\s*", "-", text)

    # Specifically target and remove trailing special characters like asterisks
    text = re.sub(r"\*+$", "", text)

    text = text.strip()

    # Ensure the first letter is capitalized if it's alphabetic
    if text and not text[0].isupper() and text[0].isalpha():
        text = text[0].upper() + text[1:]

    return text


def remove_quotes(text: str) -> str:
    """Remove quotes from a string if they exist."""
    if not text or len(text) < 2:
        return text
    quote_chars = ("'", '"', "`")
    return (
        text[1:-1] if text[0] == text[-1] and text[0] in quote_chars else text
    )
