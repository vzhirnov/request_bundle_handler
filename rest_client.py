import requests
import asyncio
import aiohttp

from collections import namedtuple


class RestClient:
    def __init__(self, host: str, headers: dict = None):
        if not host:
            raise AttributeError("Attribute host should not be empty.")
        self.host = host
        self.headers = headers

    def get(self, path: str, params=None, **kwargs):
        return self._send_request("GET", path, params=params, **kwargs)

    def post(self, path: str, json=None, **kwargs):
        return self._send_request("POST", path, json=json, **kwargs)

    def put(self, path: str, json=None, **kwargs):
        return self._send_request("PUT", path, json=json, **kwargs)

    def delete(self, path: str, json=None, **kwargs):
        return self._send_request("DELETE", path, json=json, **kwargs)

    def _send_request(self, method: str, path: str, **kwargs):
        pass


class SyncRestClient(RestClient):
    def __init__(self, host, headers):
        super().__init__(host, headers)

    def _send_request(self, method: str, path: str, **kwargs):
        url = f"{self.host}{path}"

        response = requests.request(
            method=method,
            url=url,
            headers=kwargs.pop("headers", self.headers),
            **kwargs,
        )
        return response


class AsyncRestClient(RestClient):
    def __init__(self, host, headers):
        super().__init__(host, headers)

    async def _send_request(self, method: str, path: str, **kwargs):
        url = f"{self.host}{path}"

        async with aiohttp.ClientSession(trust_env=True) as session:
            for _ in range(120):
                try:
                    async with session.request(
                            method=method,
                            url=url,
                            headers=kwargs.pop("headers", self.headers),
                            ssl=False,
                            timeout=10000000,
                            **kwargs,
                    ) as response:
                        response_body = await response.text()
                        response.body = response_body  # TODO experimental - addding body to async response
                        return response

                except Exception as e:
                    print(f"AsyncRequestHandlerFactory: An exception occured: {str(e)}")
                    await asyncio.sleep(1)
                    continue
            return response


class ProtectedRestClient(RestClient):
    def __init__(self, host, headers, request_num=None):
        super().__init__(host, headers)
        self.request_num = request_num

    async def _send_request(self, method: str, path: str, **kwargs):
        url = f"{self.host}{path}"

        Res = namedtuple(
            "FuzzResults",
            "response request_num",
        )

        async with aiohttp.ClientSession(trust_env=True) as session:
            for _ in range(120):
                try:
                    async with session.request(
                            method=method,
                            url=url,
                            headers=kwargs.pop("headers", self.headers),
                            ssl=False,
                            timeout=10000000,
                            **kwargs,
                    ) as response:
                        response_body = await response.text()
                        response.body = response_body  # TODO experimental - addding body to async response
                        return Res(response, self.request_num)

                except Exception as e:
                    print(f"AsyncRequestHandlerFactory: An exception occured: {str(e)}")
                    await asyncio.sleep(1)
                    continue
            return Res(response, self.request_num)
