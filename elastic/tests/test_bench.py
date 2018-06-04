# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import requests

from datadog_checks.elastic import ESCheck
from .common import CHECK_NAME, CONFIG, PASSWORD, URL, USER


def test_check(benchmark):
    elastic_check = ESCheck(CHECK_NAME, {}, {})

    for _ in range(3):
        try:
            elastic_check.check(CONFIG)
        except Exception:
            time.sleep(1)

    benchmark(elastic_check.check, CONFIG)


def test_pshard_metrics(benchmark):
    elastic_latency = 10
    config = {'url': URL, 'pshard_stats': True, 'username': USER, 'password': PASSWORD}

    requests.put(URL + '/_settings', data='{"index": {"number_of_replicas": 1}}')
    requests.put(URL + '/testindex/testtype/2', data='{"name": "Jane Doe", "age": 27}')
    requests.put(URL + '/testindex/testtype/1', data='{"name": "John Doe", "age": 42}')

    time.sleep(elastic_latency)
    elastic_check = ESCheck(CHECK_NAME, {}, {})

    benchmark(elastic_check.check, config)


def test_index_metrics(benchmark):
    config = {'url': URL, 'index_stats': True, 'username': USER, 'password': PASSWORD}
    elastic_check = ESCheck(CHECK_NAME, {}, {})

    benchmark(elastic_check.check, config)
