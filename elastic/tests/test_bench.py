# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

from .common import PASSWORD, URL, USER


def test_check(benchmark, dd_environment, elastic_check, instance):
    for _ in range(3):
        try:
            elastic_check.check(instance)
        except Exception:
            time.sleep(1)

    benchmark(elastic_check.check, instance)


def test_pshard_metrics(benchmark, dd_environment, elastic_check):
    instance = {'url': URL, 'pshard_stats': True, 'username': USER, 'password': PASSWORD}
    benchmark(elastic_check.check, instance)


def test_index_metrics(benchmark, dd_environment, elastic_check):
    instance = {'url': URL, 'index_stats': True, 'username': USER, 'password': PASSWORD}
    benchmark(elastic_check.check, instance)
