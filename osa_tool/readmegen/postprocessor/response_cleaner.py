import json
import re

from osa_tool.utils import logger


class JsonProcessor:
    """Utility class for robust extraction and parsing of JSON-like content from LLM responses."""

    @staticmethod
    def process_text(text: str) -> str:
        """
        Extracts JSON content from text by locating the first JSON bracket ('{' or '[')
        and the last corresponding closing bracket ('}' or ']').
        Replaces Python-style booleans/None and trims trailing commas.

        Raises:
            ValueError: If no valid JSON structure is found.
        """
        if not isinstance(text, str):
            raise ValueError("Input must be a string.")

        replacements = {"None": "null", "True": "true", "False": "false"}
        for key, value in replacements.items():
            text = text.replace(key, value)

        # remove trailing commas before closing braces/brackets
        text = re.sub(r",\s*([}\]])", r"\1", text)

        start_obj = text.find("{")
        start_arr = text.find("[")
        candidates = [pos for pos in [start_obj, start_arr] if pos != -1]

        if not candidates:
            raise ValueError("No JSON start bracket found in the input text.")

        start = min(candidates)
        open_char = text[start]
        close_char = "}" if open_char == "{" else "]"

        end = text.rfind(close_char)
        if end == -1 or end < start:
            raise ValueError("No valid JSON end bracket found in the input text.")

        return text[start : end + 1]

    @classmethod
    def parse(
        cls,
        text: str,
        expected_key: str | None = None,
        expected_type: type | None = None,
        wrap_in_list: bool = False,
    ):
        """
        Attempts to safely parse JSON from LLM response. If extraction or parsing fails,
        returns a fallback structure based on expected_type.

        Args:
            text: Raw model response.
            expected_key: Optional JSON key to extract (e.g. 'overview', 'key_files').
            expected_type: Expected type of parsed content (dict, list, str).
            wrap_in_list: If True, fallback result is wrapped in a list.

        Returns:
            Parsed content (dict | list | str) depending on context.
        """
        try:
            cleaned = cls.process_text(text)
            parsed = json.loads(cleaned)

            if expected_key:
                parsed = parsed.get(expected_key, parsed)

            if expected_type and not isinstance(parsed, expected_type):
                raise TypeError(f"Expected {expected_type}, got {type(parsed)}")

            return parsed

        except Exception as e:
            logger.warning(f"Failed to parse JSON: {e}. Applying fallback.")
            if expected_type is list or wrap_in_list:
                return [text.strip()]
            if expected_type is dict:
                key = expected_key or "raw"
                return {key: text.strip()}
            return text.strip()
