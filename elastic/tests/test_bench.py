# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

from datadog_checks.elastic import ESCheck

from .common import PASSWORD, URL, USER


def test_check(benchmark, benchmark_elastic_check, benchmark_instance, dd_run_check, dd_environment):
    for _ in range(3):
        try:
            dd_run_check(benchmark_elastic_check)
        except Exception:
            time.sleep(1)

    benchmark(benchmark_elastic_check.check, benchmark_instance)


def test_pshard_metrics(benchmark, dd_environment):
    instance = {'url': URL, 'pshard_stats': True, 'username': USER, 'password': PASSWORD}
    elastic_check = ESCheck('elastic', {}, instances=[instance])
    benchmark(elastic_check.check, instance)


def test_index_metrics(benchmark, dd_environment):
    instance = {'url': URL, 'index_stats': True, 'username': USER, 'password': PASSWORD}
    elastic_check = ESCheck('elastic', {}, instances=[instance])
    benchmark(elastic_check.check, instance)
