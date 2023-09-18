# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import threading
import time
from random import randint, randrange

import requests


def do_stuff(id, func, *args):
    while True:
        logging.info("Running %s", id)
        func(*args)
        time.sleep(randrange(20))


def run_hello():
    requests.get("http://ray-head:8000/hello")


def run_add():
    requests.post(
        "http://ray-head:8000/add",
        data=f'{{"a": {randint(1, 10)}, "b": {randint(1, 10)}}}',
        headers={'Content-Type': 'application/json'},
    )


def generate_500():
    requests.post(
        "http://ray-head:8000/add",
        data='{"a"}',
        headers={'Content-Type': 'application/json'},
    )


def generate_404():
    requests.get("http://ray-head:8000/not-found")
    time.sleep(randrange(50))


def call_openmetrics_endpoint(server):
    requests.get(f"http://{server}:8080")


if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    threads = []
    for server in ("ray-head", "ray-worker-1", "ray-worker-2", "ray-worker-3"):
        x = threading.Thread(target=do_stuff, args=(f"OM{server}", call_openmetrics_endpoint, server))
        threads.append(x)
        x.start()

    x = threading.Thread(target=do_stuff, args=("HELLO", run_hello))
    threads.append(x)
    x.start()

    x = threading.Thread(target=do_stuff, args=("ADD", run_add))
    threads.append(x)
    x.start()

    x = threading.Thread(target=do_stuff, args=("404", generate_404))
    threads.append(x)
    x.start()

    x = threading.Thread(target=do_stuff, args=("500", generate_500))
    threads.append(x)
    x.start()

    for thread in threads:
        logging.info("Waiting...")
        thread.join()
