import requests

import logger
import uuid


class RestClient:
    def __init__(self, host: str, headers: dict = None):
        if not host:
            raise AttributeError("Attribute host should not be empty.")
        self.host = host
        self.headers = headers

        self.log = logger.get_logger(__name__)

    def get(self, path: str, params=None, **kwargs):
        return self._send_request("GET", path, params=params, **kwargs)

    def post(self, path: str, json=None, **kwargs):
        return self._send_request("POST", path, json=json, **kwargs)

    def put(self, path: str, json=None, **kwargs):
        return self._send_request("PUT", path, json=json, **kwargs)

    def delete(self, path: str, json=None, **kwargs):
        return self._send_request("DELETE", path, json=json, **kwargs)

    def _send_request(self, method: str, path: str, **kwargs):
        url = f"{self.host}{path}"
        log = self.log.bind(request_id=str(uuid.uuid4()))

        response = requests.request(
            method=method,
            url=url,
            headers=kwargs.pop("headers", self.headers),
            **kwargs,
        )

        if not response.ok:
            log.error(
                "request",
                method=method,
                url=url,
                json=kwargs.get("json", None),
                params=kwargs.get("params", None),
                data=kwargs.get("data", None),
                headers=kwargs.get("headers", self.headers),
            )
            log.error(response.text)

        log.debug(
            "request",
            method=method,
            url=url,
            json=kwargs.get("json", None),
            params=kwargs.get("params", None),
            data=kwargs.get("data", None),
            headers=kwargs.get("headers", self.headers),
        )

        log.debug(
            "response",
            url=response.url,
            status_code=response.status_code,
            text=response.text,
            headers=response.headers,
            elapsed=(response.elapsed.microseconds / 1000),
        )

        return response