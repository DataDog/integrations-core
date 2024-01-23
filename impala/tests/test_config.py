# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.impala import ImpalaCheck


@pytest.mark.unit
@pytest.mark.parametrize(
    'service_type',
    [
        "unknown",
        "",
    ],
)
def test_config_unknown_service_type(service_type):
    instance = {
        "openmetrics_endpoint": "http://localhost:25000/metrics_prometheus",
        "service_type": service_type,
    }

    with pytest.raises(ConfigurationError) as exception_info:
        check = ImpalaCheck("Impala", {}, [instance])
        check.load_configuration_models()

    assert (
        exception_info.value.args[0]
        == 'Detected 1 error while loading configuration model `InstanceConfig`:\nservice_type\n  '
        'Input should be \'daemon\', \'statestore\' or \'catalog\''
    )


def test_config_service_type_mandatory():
    instance = {
        "openmetrics_endpoint": "http://localhost:25000/metrics_prometheus",
    }

    with pytest.raises(ConfigurationError) as exception_info:
        check = ImpalaCheck("Impala", {}, [instance])
        check.load_configuration_models()

    assert (
        exception_info.value.args[0]
        == 'Detected 1 error while loading configuration model `InstanceConfig`:\nservice_type\n  '
        'Field required'
    )


def test_config_service_type_can_not_be_none():
    instance = {
        "openmetrics_endpoint": "http://localhost:25000/metrics_prometheus",
        "service_type": None,
    }

    with pytest.raises(ConfigurationError) as exception_info:
        check = ImpalaCheck("Impala", {}, [instance])
        check.load_configuration_models()

    assert (
        exception_info.value.args[0]
        == 'Detected 1 error while loading configuration model `InstanceConfig`:\nservice_type\n  '
        'Input should be \'daemon\', \'statestore\' or \'catalog\''
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    'service_type',
    [
        "daemon",
        "statestore",
        "catalog",
    ],
)
def test_config_valid_service_type(service_type):
    instance = {
        "openmetrics_endpoint": "http://localhost:25000/metrics_prometheus",
        "service_type": service_type,
    }

    check = ImpalaCheck("Impala", {}, [instance])
    check.load_configuration_models()
