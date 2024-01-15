# (C) Datadog, Inc. 2024-present
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
        try:
            func(*args)
        except Exception as e:
            logging.error(e)
        time.sleep(randrange(20))


def call_hello_world():
    requests.get("http://tomcat:8080/sample/hello.jsp")


def call_404():
    requests.get("http://tomcat:8080/404")


if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    threads = []
    for index in range(5):
        x = threading.Thread(target=do_stuff, args=(f"HELLO{index}", call_hello_world))
        threads.append(x)
        x.start()

    for index in range(2):
        x = threading.Thread(target=do_stuff, args=(f"404{index}", call_404))
        threads.append(x)
        x.start()

    for thread in threads:
        logging.info("Waiting...")
        thread.join()
