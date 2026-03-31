"""Resolve a PDF source (URL or local path) to a local file path."""

from __future__ import annotations

import os
from tempfile import NamedTemporaryFile

import requests

from osa_tool.utils.logger import logger


def get_pdf_path(pdf_source: str) -> str | None:
    """Return a local file path for the given PDF source, or ``None`` on failure.

    Accepts either an HTTP(S) URL (downloads to a temp file) or a local filesystem path.
    """
    if pdf_source.lower().startswith("http"):
        return fetch_pdf_from_url(pdf_source)

    if os.path.isfile(pdf_source) and pdf_source.lower().endswith(".pdf"):
        return pdf_source

    logger.error("Invalid PDF source: %s — could not locate a valid PDF.", pdf_source)
    return None


def fetch_pdf_from_url(url: str) -> str | None:
    """Download a PDF from *url* into a temp file and return its path."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        content_type = response.headers.get("Content-Type", "")

        if response.status_code == 200 and "application/pdf" in content_type.lower():
            tmp = NamedTemporaryFile(delete=False, suffix=".pdf", prefix="downloaded_", dir=os.getcwd())
            with open(tmp.name, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return tmp.name

    except requests.exceptions.RequestException:
        logger.error("Failed to download PDF from %s", url, exc_info=True)

    return None
