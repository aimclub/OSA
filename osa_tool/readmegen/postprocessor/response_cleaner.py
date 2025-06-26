def process_text(text: str) -> str:
    """
    Extracts JSON content from the given text by locating the first opening JSON bracket
    ('{' or '[') and the last corresponding closing bracket ('}' or ']'),
    then returning the substring between them (inclusive).

    Args:
        text: The input string potentially containing JSON content.

    Returns:
        str: Extracted JSON content or raises ValueError if JSON block not detected.
    """
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
