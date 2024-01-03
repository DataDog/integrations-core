# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import threading
import time
from random import randrange

import requests


def do_stuff(id, func, *args):
    while True:
        logging.info("Running %s", id)
        func(*args)
        time.sleep(randrange(20))


def run_prediction(model):
    requests.post(
        f"http://localhost:8080/predictions/{model}",
        data='{"input": 2.0}',
        headers={'Content-Type': 'application/json'},
    )


# Will generate 5xx errors
def run_bad_prediction():
    requests.post(
        f"http://localhost:8080/predictions/{model}",
        data='{input": 2.0}',
        headers={'Content-Type': 'application/json'},
    )
    time.sleep(randrange(50))


def add_remove_model():
    requests.post("http://localhost:8081/models", params={"url": "linear_regression_3_3.mar"})
    time.sleep(150)
    requests.delete("http://localhost:8081/models/linear_regression_3_3/1")
    time.sleep(200)


def change_default_version():
    requests.put(f"http://localhost:8081/models/linear_regression_1_2/{randrange(1, 4)}/set-default")
    time.sleep(randrange(200))


def call_openmetrics_endpoint():
    requests.get("http://localhost:8082/metrics")


def run_bad_healthcheck():
    requests.get("http://localhost:8080/pin")


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
