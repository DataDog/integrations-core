# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import threading
import time
from random import randrange
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def with_query_params(url: str, params: dict[str, object]) -> str:
    return '{}?{}'.format(url, urlencode(params))


def send_request(http_request: Request) -> None:
    try:
        with urlopen(http_request) as response:
            response.read()
    except HTTPError as e:
        with e:
            e.read()


def do_stuff(id, func, *args):
    while True:
        logging.info("Running %s", id)
        func(*args)
        time.sleep(randrange(20))


def run_prediction(model):
    send_request(
        Request(
            f"http://localhost:8080/predictions/{model}",
            data=b'{"input": 2.0}',
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
    )


# Will generate 5xx errors
def run_bad_prediction():
    send_request(
        Request(
            f"http://localhost:8080/predictions/{model}",
            data=b'{input": 2.0}',
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
    )
    time.sleep(randrange(50))


def add_remove_model():
    send_request(
        Request(
            with_query_params("http://localhost:8081/models", {"url": "linear_regression_3_3.mar"}),
            method='POST',
        )
    )
    time.sleep(150)
    send_request(Request("http://localhost:8081/models/linear_regression_3_3/1", method='DELETE'))
    time.sleep(200)


def change_default_version():
    send_request(
        Request(f"http://localhost:8081/models/linear_regression_1_2/{randrange(1, 4)}/set-default", method='PUT')
    )
    time.sleep(randrange(200))


def call_openmetrics_endpoint():
    send_request(Request("http://localhost:8082/metrics", method='GET'))


def run_bad_healthcheck():
    send_request(Request("http://localhost:8080/pin", method='GET'))


if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    threads = []
    for index in range(2):
        x = threading.Thread(target=do_stuff, args=(f"OM{index}", call_openmetrics_endpoint))
        threads.append(x)
        x.start()

    for model in (
        "linear_regression_1_1",
        "linear_regression_1_2",
        "linear_regression_2_2",
        "linear_regression_2_3",
        "linear_regression_3_2",
    ):
        for index in range(3):
            x = threading.Thread(target=do_stuff, args=(f"PRED{index}-{model}", run_prediction, model))
            threads.append(x)
            x.start()

    x = threading.Thread(target=do_stuff, args=("ADD", add_remove_model))
    threads.append(x)
    x.start()

    x = threading.Thread(target=do_stuff, args=("CHANGE", change_default_version))
    threads.append(x)
    x.start()

    x = threading.Thread(target=do_stuff, args=("BADPRED", run_bad_prediction))
    threads.append(x)
    x.start()

    x = threading.Thread(target=do_stuff, args=("404", run_bad_healthcheck))
    threads.append(x)
    x.start()

    for thread in threads:
        logging.info("Waiting...")
        thread.join()
