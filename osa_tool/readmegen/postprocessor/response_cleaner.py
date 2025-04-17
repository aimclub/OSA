import re


def process_text(response: str) -> str:
    """Cleans LLM response by removing formatting quotes and unwanted prefixes."""

    # Remove leading and trailing quotes (single, double, backticks) using regex
    text = clean_llm_response(response)

    # Remove the 'plaintext' prefix
    text = remove_plaintext_prefix(text)

    # Remove the 'json' prefix
    text = remove_json_prefix(text)
    return text


def clean_llm_response(response: str) -> str:
    """
    Cleans the LLM response by removing leading and trailing quotes (single, double, or backticks)
    from the response, if they exist. The function removes multiple occurrences of quotes at the
    beginning or end of the response.

    Args:
        response: The response from the LLM that may have surrounding triple quotes.

    Returns:
        str: The cleaned response without the surrounding triple quotes.
    """
    if not response:
        return response

    cleaned_response = re.sub(r"^[\'\"`]+", "", response)  # remove leading quotes
    cleaned_response = re.sub(r"[\'\"`]+$", "", cleaned_response)

    return cleaned_response


def remove_plaintext_prefix(response: str) -> str:
    """
    Removes the 'plaintext' prefix from the beginning of the response, if present.
    """
    if response.startswith("plaintext"):
        return response[len("plaintext"):].strip()
    return response.strip()


def remove_json_prefix(response: str) -> str:
    """
    Removes the 'json' prefix from the beginning of the response, if present.
    """
    if response.startswith("json"):
        return response[len("json"):].strip()
    return response.strip()
