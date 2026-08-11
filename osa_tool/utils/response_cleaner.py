import json
import re

from json_repair import repair_json

from osa_tool.utils.logger import logger


class JsonProcessor:
    """Utility class for robust extraction and parsing of JSON-like content from LLM responses."""

    @staticmethod
    def _json_sources(text: str) -> list[str]:
        """Return raw JSON-capable text while ignoring explicitly non-JSON fences."""
        sources: list[str] = []
        position = 0
        for match in re.finditer(r"```([^\n`]*)\n(.*?)```", text, flags=re.DOTALL):
            sources.append(text[position : match.start()])
            language = match.group(1).strip().lower()
            if language in {"", "json"}:
                sources.append(match.group(2))
            position = match.end()
        sources.append(text[position:])
        return sources

    @staticmethod
    def _find_balanced_span(text: str, start: int) -> tuple[int, int] | None:
        """Return the balanced JSON object or array beginning at ``start``."""
        open_char = text[start]
        if open_char not in "{[":
            return None

        closing = {"{": "}", "[": "]"}
        stack = [open_char]
        in_string = False
        escaped = False
        for i in range(start + 1, len(text)):
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
            elif ch in "{[":
                stack.append(ch)
            elif ch in "}]":
                if not stack or closing[stack[-1]] != ch:
                    return None
                stack.pop()
                if not stack:
                    return (start, i)
        return None

    @classmethod
    def _find_balanced_roots(cls, text: str) -> list[tuple[int, int]]:
        """Find outermost complete object/array spans in a JSON-capable text source."""
        roots: list[tuple[int, int]] = []
        index = 0
        while index < len(text):
            if text[index] not in "{[":
                index += 1
                continue
            span = cls._find_balanced_span(text, index)
            if span is None:
                index += 1
                continue
            roots.append(span)
            index = span[1] + 1
        return roots

    @staticmethod
    def _root_characters(expected_type: type | None) -> set[str]:
        if expected_type is list:
            return {"["}
        if expected_type is dict:
            return {"{"}
        return {"{", "["}

    @staticmethod
    def process_text(text: str, expected_type: type | None = None) -> str:
        """
        Extracts one JSON object or array from text.
        Replaces Python-style booleans/None and trims trailing commas.
        When a JSON root is present but malformed, returns that root for
        ``json_repair`` to repair during parsing. Plain non-JSON prose is
        rejected instead of being fabricated into a JSON structure. Multiple
        complete JSON roots are rejected as ambiguous so a caller can request
        one definitive response.

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
        root_characters = JsonProcessor._root_characters(expected_type)
        complete_roots = [
            source[start : end + 1]
            for source in JsonProcessor._json_sources(text)
            for start, end in JsonProcessor._find_balanced_roots(source)
        ]
        if len(complete_roots) > 1:
            raise ValueError("Multiple complete JSON values found; return exactly one")
        if complete_roots:
            return complete_roots[0]

        starts = [
            (source.find(character), source)
            for source in JsonProcessor._json_sources(text)
            for character in root_characters
            if source.find(character) >= 0
        ]
        if not starts:
            raise ValueError("No JSON start bracket found")
        start, source = min(starts, key=lambda item: item[0])
        return source[start:]

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

        try:
            parsed = json.loads(cleaned)
        except Exception as strict_error:
            logger.error(f"JSON strict parse failed: {strict_error}")
            try:
                parsed = repair_json(json_str=cleaned, ensure_ascii=False, return_objects=True)
            except Exception as repair_error:
                logger.error(f"JSON repair parse failed: {repair_error}")
                raise JsonParseError(str(repair_error)) from repair_error

        try:
            if expected_key:
                parsed = parsed.get(expected_key, parsed)

            if expected_type and not isinstance(parsed, expected_type):
                raise TypeError(f"Expected {expected_type}, got {type(parsed)}")

            return parsed
        except Exception as exc:
            logger.error(f"JSON validation failed: {exc}")
            raise JsonParseError(str(exc)) from exc


class JsonParseError(RuntimeError):
    pass
