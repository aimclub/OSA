import os
from tempfile import NamedTemporaryFile

import requests

from osa_tool.utils import logger


def get_pdf_path(pdf_source: str) -> str | None:
    """
    Checks if the provided PDF source is a valid URL or file path.

    If the source is a URL, attempts to fetch the PDF from the URL.
    If the source is a file path, checks if the file exists and has a .pdf extension.

    Args:
        pdf_source: A URL or a file path pointing to a PDF.

    Returns:
        str | None: The path to the PDF file if valid, otherwise None.
    """
    if pdf_source.lower().startswith("http"):
        pdf_file = fetch_pdf_from_url(pdf_source)
        if pdf_file:
            return pdf_file
    elif os.path.isfile(pdf_source) and pdf_source.lower().endswith(".pdf"):
        return pdf_source

    logger.info(
        f"Invalid PDF source provided: {pdf_source}. Could not locate a valid PDF."
    )
    return None


def fetch_pdf_from_url(url: str) -> str | None:
    """
    Attempts to download a PDF file from the given URL.

    Sends a GET request to the specified URL and checks whether the response
    has a Content-Type of 'application/pdf'. If so, saves the content to a
    temporary file on disk and returns the path to the saved file.

    Args:
        url: The URL to fetch the PDF from.

    Returns:
        str | None: The file path to the downloaded PDF if successful, otherwise None.
    """
    try:
        response = requests.get(url, stream=True, timeout=10)
        content_type = response.headers.get("Content-Type", "")

        if response.status_code == 200 and "application/pdf" in content_type.lower():
            temp_pdf = NamedTemporaryFile(
                delete=False, suffix=".pdf", prefix="downloaded_", dir=os.getcwd()
            )
            with open(temp_pdf.name, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=8192):
                    pdf_file.write(chunk)

            return temp_pdf.name

    except requests.exceptions.RequestException as e:
        logger.error(f"Error accessing {url}: {e}")

    return None
