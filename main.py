import random
import time
from typing import Callable, Any

from rest_client import RestClient


class FuzzSession:
    def __init__(self, fuzzer, data_analyzer, data_saver):
        self.fuzzer = fuzzer
        self.data_analyzer = DataAnalyzer()
        self.results_saver = DataSaver()

        self.before_fuzz: Callable = Any
        self.after_fuzz: Callable = Any

    def save_results(self):
        pass

    def run(self):
        self.before_fuzz()
        pass
        self.after_fuzz()

    def show_brief_results(self):
        pass

    def save_artifacts(self):
        pass


class BaseSender:
    def __init__(self, host, path, headers, rps=0):
        self.host = host
        self.path = path
        self.headers = headers
        self.rps = rps
        self.current_rps_setter: Callable = lambda: 0

        self.need_abort = False
        self.need_suspend = False

        self.request_handler: Callable = lambda: True
        self.response_handler: Callable = lambda: True

        self.rest_client = RestClient(host, headers)
        self.response = None
        self.results_bundle = []

        self.bundle_to_resend = []

    def get_stable_rps(self):
        return self.rps

    def get_random_rps(self):
        return random.randrange(0, 5)

    def control_rps(self, mode_setter: Callable):
        time.sleep(mode_setter())

    def set_random_rps(self):
        self.current_rps_setter = self.get_random_rps

    def set_stable_rps(self):
        self.current_rps_setter = self.get_stable_rps

    def use_async_mode(self):
        pass

    @staticmethod
    def func_to_execute(slf, fun, *args, **kwargs):
        def wrapper():
            return fun(slf, *args, **kwargs)
        return wrapper

    def handle_each_request_by(self, slf, fun: Callable, *args, **kwargs):
        self.request_handler = self.func_to_execute(slf, fun, *args, **kwargs)

    def handle_each_response_by(self, slf, fun: Callable, *args, **kwargs):
        self.response_handler = self.func_to_execute(slf, fun, *args, **kwargs)

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

    def __init__(self, method, json_bundle, host, path, headers, rps):
        super().__init__(host, path, headers, rps)

        if method not in ["POST", "PUT", "DELETE"]:
            raise AttributeError(f'Attribute method should be on of {["POST", "PUT", "DELETE"]}.')
        self.method = method

        self.send_with_method = {
            "POST": self.rest_client.post,
            "PUT": self.rest_client.put,
            "DELETE": self.rest_client.delete
        }
        self.json_bundle = json_bundle

    def start(self):
        for json in self.json_bundle:
            self.control_rps(self.current_rps_setter)

            if self.need_abort:
                break
            elif self.need_suspend:
                while self.need_suspend:
                    time.sleep(0.5)

            self.request_handler()
            self.response = self.send_with_method[self.method](self.path, json=json)
            self.response_handler()

            self.results_bundle.append(self.response)

    def stop(self):
        self.need_abort = True

    def suspend(self):
        self.need_suspend = True

    def go_on(self):
        self.need_suspend = False

    """
    gets bundle of data to send, e.g. bundle of jsons
    Can:
        send data with strong RPS
        send data with random RPS(can change mode by users decision)
        send data in synchronous mode
        send data in asynchronous mode
        send data in mixed mode(async, but sync or by condition)

        attach request handler
        attach response handler
    """

    def _make_sync_requests(self, bundle):
        for json in bundle:
            self.request_handler()
            self.response = self.rest_client.post(self.path, json=json)
            self.response_handler()

            self._response_bundle.append(self.response)

    def _make_async_requests(self, start_with: int):
        pass


if __name__ == "__main__":
    jb = [{"data": "Hello Beeceptor"} for x in range(0, 10)]
    rs = JsonSender(
        method="POST",
        json_bundle=jb,
        host="https://mytest.free.beeceptor.com/",
        path='my/api/path',
        headers={},
        rps=1
    )

    def p(js: JsonSender, secs):
        print("HERE")
        if not js.response.ok:
            print("NOT OK")
        js.suspend()
        time.sleep(secs)
        js.go_on()

    rs.handle_each_response_by(rs, p, 0)
    rs.start()
