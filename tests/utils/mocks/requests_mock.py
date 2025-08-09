from unittest.mock import Mock

from requests import HTTPError


def mock_requests_response(status_code, json_data=None):
    """
    Factory to create a mocked requests.Response object with a specified status code.
    It will raise HTTPError when raise_for_status() is called if status_code >= 400.
    """
    mock_resp = Mock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data or {}

    def raise_for_status():
        if 400 <= status_code < 600:
            http_error = HTTPError(f"{status_code} Error")
            http_error.response = mock_resp
            raise http_error

    mock_resp.raise_for_status = raise_for_status
    return mock_resp
