from unittest.mock import Mock

from requests import HTTPError


def mock_requests_response(
    status_code: int,
    json_data=None,
    headers=None,
    content_iter=None,
    text_data=None,
    **kwargs,
):
    """
    Factory to create a mocked requests.Response object with a specified status code.

    Supports json(), headers, iter_content, text.
    Raises HTTPError when raise_for_status() is called if status_code >= 400.
    Extra kwargs are ignored (for forward-compatibility).
    """
    mock_resp = Mock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data or {}
    mock_resp.headers = headers or {}
    mock_resp.iter_content = content_iter or (lambda chunk_size: [])
    mock_resp.text = text_data or ""

    def raise_for_status():
        if 400 <= status_code < 600:
            http_error = HTTPError(f"{status_code} Error")
            http_error.response = mock_resp
            raise http_error

    mock_resp.raise_for_status = raise_for_status
    return mock_resp
