import abc
from collections.abc import Collection
import logging
from string import Formatter
from typing import Any

import requests
from requests import RequestException


logger = logging.getLogger(__name__)


class Endpoint(abc.ABC):
    def __init__(self, url: str, param_names: Collection[str] = None):
        if param_names is not None:
            param_names = tuple(param_names)
        self.url = url
        self.param_names = param_names
        self.url_params = (fname for _, fname, _, _ in Formatter().parse(self.url) if fname)

    def _check_params(self, params: dict[str, Any]) -> None:
        if self.param_names is None:
            return

        missing_params = set(self.param_names).difference(set(params))
        extra_params = set(params).difference(set(self.param_names))

        error_msg = f"{self.__class__.__name__} {self.url}."
        is_error = False

        if missing_params:
            error_msg += f'\nMissing params: ({", ".join(missing_params)}).'
            is_error = True

        """
        не все параметры при запросах обязательны
        if extra_params:
            error_msg += f'\nUnexpected params: ({", ".join(extra_params)}).'
            is_error = True
        """
        if is_error:
            raise ValueError(error_msg)

    def _parse_url_params(self, params):
        url_params = {fname: params.pop(fname) for fname in self.url_params}
        url = self.url
        if url_params:
            url = self.url.format(**url_params)
        return url, params

    def __call__(self, json_data: dict | None = None, **params) -> Any:
        self._check_params(params)
        url, params = self._parse_url_params(params)
        result = self._execute_request(url, params=params, json_data=json_data)
        if result.status_code != 200:
            logger.error(f"url: {url}")
            logger.error(f"params: {params}")
            logger.error(f"json_data: {json_data}")
            raise RequestException(result.status_code)
        return result.json()

    @abc.abstractmethod
    def _execute_request(url: str, params: dict[str, Any]) -> requests.Request:
        raise NotImplementedError


class GetEndpoint(Endpoint):
    def _execute_request(
        self,
        url: str,
        params: dict[str, Any],
        json: dict | None = None,
    ) -> requests.Response:
        return requests.get(
            url,
            params=params,
            json=json,
            headers={"accept": "application/json"},
        )


class PostEndpoint(Endpoint):
    def _execute_request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        json_data: dict | None = None,
    ) -> requests.Response:
        return requests.post(
            url,
            params=params,
            json=json_data,
            headers={"accept": "application/json"},
        )
