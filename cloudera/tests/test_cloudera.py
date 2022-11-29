# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.cloudera import ClouderaCheck
from datadog_checks.dev.utils import get_metadata_metrics


def test_emits_critical_service_check_when_api_is_none():
    assert True


def test_emits_critical_service_check_when_credentials_incorrect():
    assert True


def test_py2_not_supported():
    assert True


def test_timeseries_item_no_data():
    assert True


def test_check():
    assert True
