# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.tracking import tracked_method


def agent_check_getter(self):
    return self.check


class TestAgentCheck(AgentCheck):
    def __init__(self, debug_stats_kwargs):
        self._debug_stats_kwargs = debug_stats_kwargs
        super(TestAgentCheck, self).__init__()

    def debug_stats_kwargs(self):
        return self._debug_stats_kwargs


class TestJob:
    def __init__(self, check):
        self.check = check

    def run_job(self):
        self.do_work()
        self.do_work_return_list()
        try:
            self.test_tracked_exception()
        except Exception:
            return

    @tracked_method("hello", agent_check_getter=agent_check_getter)
    def do_work(self):
        return 5

    @tracked_method("hello", agent_check_getter=agent_check_getter, track_result_length=True)
    def do_work_return_list(self):
        return list(range(5))

    @tracked_method("hello", agent_check_getter=agent_check_getter)
    def test_tracked_exception(self):
        raise Exception("oops")


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
def test_tracked_method(aggregator, debug_stats_kwargs):
    check = TestAgentCheck(debug_stats_kwargs) if debug_stats_kwargs else AgentCheck()
    job = TestJob(check)
    job.run_job()

    tags = debug_stats_kwargs.pop('tags', [])
    hostname = debug_stats_kwargs.pop('hostname', None)

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
        tags=tags + ["operation:test_tracked_exception", "error:<class 'Exception'>"],
    )
