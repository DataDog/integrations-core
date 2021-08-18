# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager


def mock_executor(result=()):
    def executor(_):
        return result

    return executor


def create_query_manager(*args, **kwargs):
    executor = kwargs.pop('executor', None)
    if executor is None:
        executor = mock_executor()

    check = kwargs.pop('check', None) or AgentCheck('test', {}, [{}])
    check.check_id = 'test:instance'

    return QueryManager(check, executor, args, **kwargs)
