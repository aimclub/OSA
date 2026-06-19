import json
import re

from osa_tool.utils.logger import logger


class JsonProcessor:
    """Utility class for robust extraction and parsing of JSON-like content from LLM responses."""

    @staticmethod
    def _extract_from_fence(text: str) -> str | None:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _find_balanced_span(text: str, open_char: str) -> tuple[int, int] | None:
        close_char = "}" if open_char == "{" else "]"
        start = text.find(open_char)
        if start == -1:
            return None

        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return (start, i)
        return None

    @staticmethod
    def process_text(text: str, expected_type: type | None = None) -> str:
        """
        Extracts JSON content from text by locating the first JSON bracket ('{' or '[')
        and the last corresponding closing bracket ('}' or ']').
        Replaces Python-style booleans/None and trims trailing commas.

        Raises:
            ValueError: If no valid JSON structure is found.
        """
        if not isinstance(text, str):
            raise ValueError("Input must be a string.")

        # Strip raw control characters that are invalid in JSON string values.
        # Preserves \t (0x09), \n (0x0A), \r (0x0D) which JSON parsers accept unescaped.
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        fenced = JsonProcessor._extract_from_fence(text)
        if fenced:
            text = fenced

        replacements = {"None": "null", "True": "true", "False": "false"}
        for key, value in replacements.items():
            text = text.replace(key, value)

        # remove trailing commas before closing braces/brackets
        text = re.sub(r",\s*([}\]])", r"\1", text)
        text = text.strip()

        preferred: list[str]
        if expected_type is list:
            preferred = ["["]
        elif expected_type is dict:
            preferred = ["{"]
        else:
            preferred = ["[", "{"]

        for open_char in preferred + [c for c in ["[", "{"] if c not in preferred]:
            span = JsonProcessor._find_balanced_span(text, open_char)
            if span:
                start, end = span
                return text[start : end + 1]

        if expected_type is list:
            logger.error("No JSON start bracket found, adding '[' at the beginning")
            if not text.startswith("["):
                text = "[" + text
            if not text.endswith("]"):
                logger.error("No valid JSON end bracket found, adding ']' at the end")
                text = text + "]"
            return text

        logger.error("No JSON start bracket found, adding '{' at the beginning")
        if not text.startswith("{"):
            text = "{" + text
        if not text.endswith("}"):
            logger.error("No valid JSON end bracket found, adding '}' at the end")
            text = text + "}"
        return text

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
            cleaned = cls.process_text(text, expected_type=expected_type)
            parsed = json.loads(cleaned)

            if expected_key:
                parsed = parsed.get(expected_key, parsed)

            if expected_type and not isinstance(parsed, expected_type):
                raise TypeError(f"Expected {expected_type}, got {type(parsed)}")

            return parsed

        except Exception as e:
            logger.error(f"JSON strict parse failed: {e}")
            raise JsonParseError(str(e)) from e


class JsonParseError(RuntimeError):
    pass
