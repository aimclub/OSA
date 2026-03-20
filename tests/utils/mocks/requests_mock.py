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
    
    This method is used for testing HTTP client interactions by simulating responses from the requests library. It configures a mock object to mimic key attributes and methods of a real Response, allowing control over status codes, JSON data, headers, content streaming, and text content. An HTTPError is raised when raise_for_status() is called if the status code indicates a client or server error (400-599), mirroring real request behavior. Extra keyword arguments are ignored to maintain forward compatibility with potential future extensions.
    
    Args:
        status_code: The HTTP status code to assign to the mock response.
        json_data: Data to be returned by the json() method. Defaults to an empty dictionary.
        headers: HTTP headers to assign to the mock response. Defaults to an empty dictionary.
        content_iter: A callable that simulates iter_content for streaming response content. Defaults to a lambda returning an empty list.
        text_data: Text content to assign to the mock response's text attribute. Defaults to an empty string.
        **kwargs: Additional keyword arguments are ignored for forward compatibility.
    
    Returns:
        A Mock object configured to mimic a requests.Response with the specified properties.
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
