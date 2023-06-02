# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dcgm.metrics import METRIC_MAP
from datadog_checks.dev import get_here

INSTANCE = {
    "openmetrics_endpoint": "http://localhost:9400/metrics",
}

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')


# This function creates an array of the value of the json
# and cuts the array at n
def show_first_n_rows(json_data, n):
    metric_value = []
    for _key, value in json_data.items():
        metric_value.append(value)
    else:
        print("error")
    metric_value_N = metric_value[:n]
    return metric_value_N


# I only want to include the metrics that are exposed:
METRICS = show_first_n_rows(METRIC_MAP, 16)

print(METRICS)
