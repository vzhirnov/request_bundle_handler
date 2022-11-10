import time
import random
import asyncio

from typing import Callable, Union
from rest_client import SyncRestClient, AsyncRestClient, ProtectedRestClient

from aiohttp.client_reqrep import ClientResponse
from requests.models import Response


class BaseSender:
    """
    gets bundle of data to send
    returns bundle of responses
    Can:
        send data with strong RPS
        send data with random RPS(can change mode by users decision)
        send data in synchronous mode
        send data in asynchronous mode
        send data in mixed mode(async, but sync or by condition)

        attach request handler
        attach response handler
    """

    def __init__(self, host, path, headers, rps, send_mode):
        self.host = host
        self.path = path
        self.headers = headers
        self.rps = 1 / rps

        self.need_abort = False
        self.need_suspend = False

        self.request_handler: Callable = lambda: True
        self.response_handler: Callable = lambda: True

        self.sync_rest_client = SyncRestClient(host, headers)
        self.async_rest_client = AsyncRestClient(host, headers)
        self.protected_rest_client = ProtectedRestClient(host, headers)

        self.response = Union[ClientResponse, Response]
        self.results_bundle = []

        self.bundle_to_resend = []
        self.conditions_for_resend = []

        if send_mode not in ["SYNC", "ASYNC", "PROTECTED"]:
            raise AttributeError(f'Attribute send_mode should be on of {["SYNC", "ASYNC", "PROTECTED"]}.')

        self.send_mode = send_mode
        self.current_rps_setter = \
            self.make_async_rps if any([self.send_mode == x for x in ["ASYNC", "PROTECTED"]]) else self.make_sync_rps

    def send_sync_with_method(self, method):
        senders = {
            "POST": self.sync_rest_client.post,
            "PUT": self.sync_rest_client.put,
            "DELETE": self.sync_rest_client.delete
        }
        return senders[method]

    def send_async_with_method(self, method):
        senders = {
            "POST": self.async_rest_client.post,
            "PUT": self.async_rest_client.put,
            "DELETE": self.async_rest_client.delete
        }
        return senders[method]

    def send_protected_with_method(self, method, request_num=0):
        self.protected_rest_client.request_num = request_num
        senders = {
            "POST": self.protected_rest_client.post,
            "PUT": self.protected_rest_client.put,
            "DELETE": self.protected_rest_client.delete
        }
        return senders[method]

    def get_response(self):
        return self.response

    def set_rps(self, rps):
        self.rps = rps

    def make_sync_rps(self, rand=False):
        time.sleep(self.rps if rand is False else random.randrange(0, 5))

    async def make_async_rps(self, rand=False):
        await asyncio.sleep(self.rps if rand is False else random.randrange(0, 5))

    def control_rps(self, mode_setter: Callable):
        mode_setter()

    async def control_async_rps(self, mode_setter: Callable):
        await mode_setter()

    @staticmethod
    def _func_to_execute(slf, fun, *args, **kwargs):  # TODO make all req methods private _
        def wrapper():
            return fun(slf, *args, **kwargs)
        return wrapper

    def handle_each_request_by(self, slf, fun: Callable, *args, **kwargs):
        self.request_handler = self._func_to_execute(slf, fun, *args, **kwargs)

    def handle_each_response_by(self, slf, fun: Callable, *args, **kwargs):
        self.response_handler = self._func_to_execute(slf, fun, *args, **kwargs)

    def start(self):
        pass

    def stop(self):
        pass

    def suspend(self):
        pass

    def go_on(self):
        pass


class JsonSender(BaseSender):
    """
    POST, PUT, DELETE types are supported
    """

    def __init__(self, method, json_bundle, host, path, headers, rps, send_mode):
        super().__init__(host, path, headers, rps, send_mode)

        if method not in ["POST", "PUT", "DELETE"]:
            raise AttributeError(f'Attribute method should be on of {["POST", "PUT", "DELETE"]}.')
        self.method = method

        self.json_bundle = json_bundle

    async def start_in_protected_mode(self, json_bundle):
        self.current_rps_setter = self.make_async_rps

        request_tasks = [
            self.send_protected_with_method(self.method, request_num=request_num)(self.path, json=json)
            for request_num, json in enumerate(json_bundle)
        ]
        for f in request_tasks:
            await self.control_async_rps(self.current_rps_setter)

            if self.need_abort:
                break
            elif self.need_suspend:
                while self.need_suspend:
                    await asyncio.sleep(0.5)

            self.request_handler()
            res = await f
            self.response = res.response
            self.response_handler()

            if any([condition for condition in self.conditions_for_resend]):
            # if self.response.status != 200:
                self.bundle_to_resend.append(res.request_num)
            else:
                self.results_bundle.append(self.response)

        if self.bundle_to_resend:
            print(
                f"\nGot requests with response status 500 (in the amount of {len(self.bundle_to_resend)}), "
                f"resend them for additional check:",
                end="\n",
            )

            self.start_in_sync_mode(self.bundle_to_resend)

    async def start_in_async_mode(self, json_bundle):
        self.current_rps_setter = self.make_async_rps

        request_tasks = [
            self.send_async_with_method(self.method)(self.path, json=json)
            for json in json_bundle
        ]
        for f in request_tasks:
            await self.control_async_rps(self.current_rps_setter)

            if self.need_abort:
                break
            elif self.need_suspend:
                while self.need_suspend:
                    await asyncio.sleep(0.5)

            self.request_handler()
            self.response = await f
            self.response_handler()

            self.results_bundle.append(self.response)

    def start_in_sync_mode(self, json_bundle):
        self.current_rps_setter = self.make_sync_rps

        for json in json_bundle:
            self.control_rps(self.current_rps_setter)

            if self.need_abort:
                break
            elif self.need_suspend:
                while self.need_suspend:
                    time.sleep(0.5)

            self.request_handler()
            self.response = self.send_sync_with_method(self.method)(self.path, json=json)
            self.response_handler()

            self.results_bundle.append(self.response)

    def start(self):
        if self.send_mode == "SYNC":
            self.start_in_sync_mode(self.json_bundle)
        elif self.send_mode == "ASYNC":
            asyncio.run(self.start_in_async_mode(self.json_bundle))
        else:
            asyncio.run(self.start_in_protected_mode(self.json_bundle))

    def stop(self):
        self.need_abort = True

    def suspend(self):
        self.need_suspend = True

    def go_on(self):
        self.need_suspend = False


if __name__ == "__main__":

    jb = [{"data": "Hello Beeceptor"} for x in range(0, 5)]
    rs = JsonSender(
        method="POST",
        json_bundle=jb,
        host="http://localhost:8080",
        path='/',
        headers={},
        rps=100,
        send_mode="PROTECTED"
    )

    def p(js: JsonSender, secs):
        js.conditions_for_resend.append(not js.get_response().ok)
        if not js.get_response().ok:
            print("GOT NOT OK answer...")
        js.suspend()
        time.sleep(secs)
        js.go_on()
    rs.handle_each_response_by(rs, p, 0)
    rs.start()
