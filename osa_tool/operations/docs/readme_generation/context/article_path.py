import os
from tempfile import NamedTemporaryFile

import requests

from osa_tool.utils.logger import logger


def get_pdf_path(pdf_source: str) -> str | None:
    """
    Checks if the provided PDF source is a valid URL or file path and returns a local file path if valid.
    
    If the source is a URL, attempts to download the PDF from the URL via a helper function that validates the Content-Type header to ensure it is a PDF. If successful, returns the path to the downloaded temporary file.
    If the source is a file path, checks if the file exists on disk and has a .pdf extension. If both conditions are met, returns the same file path.
    
    WHY: This method centralizes validation and retrieval of PDF sources, ensuring that only verified PDF files (either from a URL or local disk) are processed further, preventing errors downstream.
    
    Args:
        pdf_source: A URL (starting with "http") or a local file path pointing to a PDF.
    
    Returns:
        str | None: The path to a valid PDF file if the source is a valid URL or an existing local PDF file; otherwise None. Returns None if the URL cannot be fetched, the file does not exist, or the file extension is not .pdf.
    """
    if pdf_source.lower().startswith("http"):
        pdf_file = fetch_pdf_from_url(pdf_source)
        if pdf_file:
            return pdf_file
    elif os.path.isfile(pdf_source) and pdf_source.lower().endswith(".pdf"):
        return pdf_source

    logger.error(f"Invalid PDF source provided: {pdf_source}. Could not locate a valid PDF.")
    return None


def fetch_pdf_from_url(url: str) -> str | None:
    """
    Attempts to download a PDF file from the given URL.
    
    Sends a GET request with streaming enabled to the specified URL and checks whether the response has a Content-Type of 'application/pdf'. If so, saves the content to a temporary file on disk and returns the path to the saved file. The method uses a timeout to avoid hanging indefinitely on unresponsive servers.
    
    WHY: This method ensures that only valid PDF files are downloaded by verifying the Content-Type header, preventing the saving of non-PDF content (e.g., HTML error pages) as PDF files.
    
    Args:
        url: The URL to fetch the PDF from.
    
    Returns:
        str | None: The file path to the downloaded PDF if successful, otherwise None. Returns None if the request fails, the status code is not 200, the Content-Type is not 'application/pdf', or any network/request exception occurs.
    
    Raises:
        This method catches and logs requests.exceptions.RequestException internally, so no exceptions are propagated to the caller.
    """
    try:
        response = requests.get(url, stream=True, timeout=10)
        content_type = response.headers.get("Content-Type", "")

        if response.status_code == 200 and "application/pdf" in content_type.lower():
            temp_pdf = NamedTemporaryFile(delete=False, suffix=".pdf", prefix="downloaded_", dir=os.getcwd())
            with open(temp_pdf.name, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=8192):
                    pdf_file.write(chunk)

            return temp_pdf.name

    except requests.exceptions.RequestException as e:
        logger.error(f"Error accessing {url}: {e}")

    return None
