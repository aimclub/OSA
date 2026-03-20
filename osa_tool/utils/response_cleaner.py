import json
import re

from osa_tool.utils.logger import logger


class JsonProcessor:
    """
    Utility class for robust extraction and parsing of JSON-like content from LLM responses.
    """


    @staticmethod
    def process_text(text: str) -> str:
        """
        Extracts JSON content from text by locating the first JSON bracket ('{' or '[')
        and the last corresponding closing bracket ('}' or ']').
        Replaces Python-style booleans/None and trims trailing commas.
        
        This method is designed to clean and extract a valid JSON substring from potentially malformed or embedded text (e.g., output from an LLM or log). It handles common non‑JSON patterns like Python‑style literals and trailing commas to produce a string that can be parsed by a standard JSON decoder.
        
        Args:
            text: The input string that may contain JSON content, possibly with Python‑style literals (True/False/None) or trailing commas.
        
        Returns:
            The extracted JSON substring, cleaned and ready for parsing. If no opening bracket is found, a default '{' is added at the start; if no matching closing bracket is found, the appropriate bracket is added at the end.
        
        Raises:
            ValueError: If the input is not a string, or if no valid JSON structure can be extracted (after the fallback additions).
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
            logger.error("No JSON start bracket found, adding '{' at the beginning")
            text = "{" + text
            candidates = [0]

        start = min(candidates)
        open_char = text[start]
        close_char = "}" if open_char == "{" else "]"

        end = text.rfind(close_char)
        if end == -1 or end < start:
            logger.error(f"No valid JSON end bracket found, adding '{close_char}' at the end")
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
        Attempts to safely parse JSON from an LLM response string. If extraction or parsing fails, raises a JsonParseError.
        
        This method first cleans the input text to isolate a JSON structure, then parses it. If an `expected_key` is provided, it attempts to extract the value associated with that key from the parsed object; if the key is not found, the entire parsed object is returned. If an `expected_type` is provided, the final result is validated against that type.
        
        Args:
            text: The raw string response from the model, which may contain surrounding text or formatting.
            expected_key: An optional key to look up within the parsed JSON object. If provided, the method returns `parsed[expected_key]` if it exists; otherwise, it returns the full `parsed` object.
            expected_type: An optional type (e.g., dict, list, str) to validate the final parsed content against. If the content does not match, a TypeError is raised.
        
        Returns:
            The parsed JSON content, which could be a dict, list, or str, depending on the input and the optional `expected_key`.
        
        Raises:
            JsonParseError: If the text cannot be cleaned to extract a valid JSON structure, if the JSON is malformed, or if a TypeError is raised due to a type mismatch.
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
            logger.error(f"JSON strict parse failed: {e}")
            raise JsonParseError(str(e)) from e


class JsonParseError(RuntimeError):
    """
    Custom exception raised when JSON parsing fails.
    
        This exception provides additional context about the parsing failure, such as the
        JSON string that caused the error and the specific parsing issue encountered.
    
        Attributes:
            json_string: The JSON string that could not be parsed.
            message: A description of the parsing error.
    
        Methods:
            __init__: Initializes the exception with the problematic JSON string and an error message.
            __str__: Returns a formatted string representation of the exception.
    """

    pass
