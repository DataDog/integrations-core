# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kubevirt_api import KubevirtApiCheck

from .conftest import mock_http_responses

pytestmark = [pytest.mark.unit]


def test_check(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)

    check = KubevirtApiCheck("kubevirt_api", {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric("kubevirt_api.can_connect", value=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_emits_zero_can_connect_when_service_is_down(dd_run_check, aggregator, instance):
    check = KubevirtApiCheck("kubevirt_api", {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)
        aggregator.assert_metric("kubevirt_api.can_connect", value=0)
