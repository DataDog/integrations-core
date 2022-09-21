# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.tracking import tracked_method


def agent_check_getter(self):
    return self.check


class HelloCheck(AgentCheck):
    def __init__(self, debug_stats_kwargs):
        self._debug_stats_kwargs = debug_stats_kwargs
        super(HelloCheck, self).__init__(name="hello")

    def debug_stats_kwargs(self):
        return self._debug_stats_kwargs


EXPECTED_RESULT = 5


class MyException(Exception):
    pass


class TestJob:
    def __init__(self, check):
        self.check = check

    def run_job(self):
        result = self.do_work()
        self.do_work_return_list()
        try:
            self.test_tracked_exception()
        except Exception:
            pass

        return result

    @tracked_method(agent_check_getter=agent_check_getter)
    def do_work(self):
        return EXPECTED_RESULT

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def do_work_return_list(self):
        return list(range(5))

    @tracked_method(agent_check_getter=agent_check_getter)
    def test_tracked_exception(self):
        raise MyException("oops")


@pytest.mark.parametrize(
    "debug_stats_kwargs",
    [
        {},
        {
            "tags": ["hey:there"],
            "hostname": "tiberius",
        },
    ],
)
@pytest.mark.parametrize("disable_tracking", [True, False])
def test_tracked_method(aggregator, debug_stats_kwargs, disable_tracking):
    os.environ['DD_DISABLE_TRACKED_METHOD'] = str(disable_tracking).lower()
    check = HelloCheck(debug_stats_kwargs) if debug_stats_kwargs else AgentCheck(name="hello")
    job = TestJob(check)
    result = job.run_job()
    assert result == EXPECTED_RESULT

    tags = debug_stats_kwargs.pop('tags', [])
    hostname = debug_stats_kwargs.pop('hostname', None)

    if disable_tracking:
        for m in ["dd.hello.operation.time", "dd.hello.operation.result.length", "dd.hello.operation.error"]:
            assert not aggregator.metrics(m), "when tracking is disabled these metrics should not be recorded"
    else:
        aggregator.assert_metric("dd.hello.operation.time", hostname=hostname, tags=tags + ["operation:do_work"])
        aggregator.assert_metric(
            "dd.hello.operation.time", hostname=hostname, tags=tags + ["operation:do_work_return_list"]
        )
        aggregator.assert_metric(
            "dd.hello.operation.result.length", hostname=hostname, tags=tags + ["operation:do_work_return_list"]
        )
        aggregator.assert_metric(
            "dd.hello.operation.error",
            hostname=hostname,
            tags=tags
            + ["operation:test_tracked_exception", "error:<class 'tests.base.utils.test_tracking.MyException'>"],
        )
