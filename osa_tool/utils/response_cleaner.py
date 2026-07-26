import json
import re

from osa_tool.utils.logger import logger


class JsonProcessor:
    """Utility class for robust extraction and parsing of JSON-like content from LLM responses."""

    @staticmethod
    def _extract_from_fence(text: str) -> str | None:
        candidates: list[tuple[bool, str]] = []
        for match in re.finditer(r"```([^\n`]*)\n(.*?)```", text, flags=re.DOTALL):
            language = match.group(1).strip().lower()
            if language not in {"", "json"}:
                continue
            candidate = match.group(2).strip()
            spans = [
                span for char in ("{", "[") if (span := JsonProcessor._find_balanced_span(candidate, char)) is not None
            ]
            if not spans:
                continue
            start, end = min(spans, key=lambda span: span[0])
            payload = candidate[start : end + 1]
            try:
                json.loads(payload)
            except json.JSONDecodeError:
                continue
            candidates.append((language == "json", payload))
        for explicitly_json in (True, False):
            for is_json, payload in candidates:
                if is_json == explicitly_json:
                    return payload
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
        text = text.strip()
        fenced = JsonProcessor._extract_from_fence(text)
        if fenced:
            text = fenced

        preferred: list[str]
        if expected_type is list:
            preferred = ["["]
        elif expected_type is dict:
            preferred = ["{"]
        else:
            # With no type information, preserve the outermost/earliest JSON root.
            starts = [(text.find(char), char) for char in ("{", "[") if text.find(char) >= 0]
            preferred = [char for _index, char in sorted(starts)]

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
            # expected_type applies after expected_key lookup, not to the keyed envelope.
            cleaned = cls.process_text(text, expected_type=dict if expected_key else expected_type)
        except Exception as exc:
            logger.error(f"JSON extraction failed: {exc}")
            raise JsonParseError(str(exc)) from exc

        last_error: Exception | None = None
        for candidate in (cleaned, cls._fix_unterminated_strings(cleaned)):
            try:
                parsed = json.loads(candidate)

                if expected_key:
                    parsed = parsed.get(expected_key, parsed)

                if expected_type and not isinstance(parsed, expected_type):
                    raise TypeError(f"Expected {expected_type}, got {type(parsed)}")

                return parsed

            except Exception as exc:
                last_error = exc
                logger.error(f"JSON strict parse failed: {exc}")
        raise JsonParseError(str(last_error)) from last_error

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
