# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.kubevirt_controller import KubevirtControllerCheck

from .conftest import mock_http_responses


def test_emits_can_connect_one_when_service_is_up(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)
    check = KubevirtControllerCheck("kubevirt_controller", {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        "kubevirt_controller.can_connect",
        value=1,
        tags=[
            "endpoint:https://10.244.0.38:443/healthz",
        ],
    )


def test_emits_can_connect_zero_when_service_is_down(dd_run_check, aggregator, instance):
    check = KubevirtControllerCheck("kubevirt_controller", {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)
    aggregator.assert_metric(
        "kubevirt_controller.can_connect", value=0, tags=["endpoint:https://10.244.0.38:443/healthz"]
    )
