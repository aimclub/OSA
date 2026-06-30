import json
import re

from osa_tool.utils.logger import logger


class JsonProcessor:
    """Utility class for robust extraction and parsing of JSON-like content from LLM responses."""

    @staticmethod
    def process_text(text: str) -> str:
        """
        Extracts JSON content from text by locating the first JSON bracket ('{' or '[')
        and the last corresponding closing bracket ('}' or ']').
        Replaces Python-style booleans/None and trims trailing commas.
        For small models that don't return JSON, wraps response as {"result": text}.

        Raises:
            ValueError: If no valid JSON structure is found.
        """
        if not isinstance(text, str):
            raise ValueError("Input must be a string.")

        # Strip raw control characters that are invalid in JSON string values.
        # Preserves \t (0x09), \n (0x0A), \r (0x0D) which JSON parsers accept unescaped.
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

        replacements = {"None": "null", "True": "true", "False": "false"}
        for key, value in replacements.items():
            text = text.replace(key, value)

        # remove trailing commas before closing braces/brackets
        text = re.sub(r",\s*([}\]])", r"\1", text)

        start_obj = text.find("{")
        start_arr = text.find("[")
        candidates = [pos for pos in [start_obj, start_arr] if pos != -1]

        if not candidates:
            raise ValueError("No JSON brackets found in LLM response")

        start = min(candidates)
        open_char = text[start]
        close_char = "}" if open_char == "{" else "]"

        end = text.rfind(close_char)
        if end == -1 or end < start:
            logger.warning(f"Incomplete JSON found, auto-closing with '{close_char}'")
            text = text + close_char
            end = len(text) - 1

        return text[start : end + 1]

    @classmethod
    def parse(
        cls,
        text: str,
        expected_key: str | None = None,
        expected_type: type | None = None,
    ):
        """
        Attempts to safely parse JSON from LLM response. If extraction or parsing fails, raises Error.

        Args:
            text: Raw model response.
            expected_key: Optional JSON key to extract (e.g. 'overview', 'key_files').
            expected_type: Expected type of parsed content (dict, list, str).

        Returns:
            Parsed content (dict | list | str) depending on context.
        """
        try:
            cleaned = cls.process_text(text)
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError as je:
                logger.warning(f"Initial JSON parse failed: {je}. Attempting recovery...")
                cleaned = cls._fix_unterminated_strings(cleaned)
                parsed = json.loads(cleaned)

            if expected_key:
                parsed = parsed.get(expected_key, parsed)

            if expected_type and not isinstance(parsed, expected_type):
                raise TypeError(f"Expected {expected_type}, got {type(parsed)}")

            return parsed

        except Exception as e:
            logger.error(f"JSON strict parse failed: {e}")
            raise JsonParseError(str(e)) from e

    @staticmethod
    def _fix_unterminated_strings(text: str) -> str:
        """Fix common JSON issues: unterminated strings, missing quotes."""
        import re

        text = re.sub(r':\s*"([^"]*?)(\n|,|})', r': "\1"\2', text)
        # Exclude JSON keywords true/false/null from string-quoting to avoid bool→string corruption
        text = re.sub(r":\s*(?!true\b|false\b|null\b)([a-zA-Z_][a-zA-Z0-9_]*)\s*([,}])", r': "\1"\2', text)
        text = text.rstrip('"') + '"' if text.count('"') % 2 == 1 else text
        return text


class JsonParseError(RuntimeError):
    pass
