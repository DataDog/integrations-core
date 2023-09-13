# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import random
import time

import ray


@ray.remote
def echo_sleep(x):
    print(f"{time.time()} - {x}")
    time.sleep(x)
    return x


# create a file for the healthcheck
with open("/tmp/running", "w+"):
    pass

while True:
    ray.init(address="ray://ray-head:10001")

    result_ids = []
    for i in range(random.randint(3, 10)):
        result_ids.append(echo_sleep.remote(i))

    # Wait for the tasks to complete and retrieve the results.
    print(f"{time.time()} - {ray.get(result_ids)}")

    ray.shutdown()

    print(f"{time.time()} - Sleeping for 30 seconds")
    time.sleep(30)
