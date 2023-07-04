# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'instance, error_message',
    [
        pytest.param(
            {},
            "No endpoint configured. You need to configure one of these options: "
            "openmetrics_endpoint, inference_api_url or management_api_url.",
            id='empty config',
        ),
        pytest.param(
            {"option"},
            "No endpoint configured. You need to configure one of these options: "
            "openmetrics_endpoint, inference_api_url or management_api_url.",
            id='no endpoint configured',
        ),
        pytest.param(
            {"openmetrics_endpoint", "inference_api_url"},
            "Too many endpoints configured for this instance: \\['openmetrics_endpoint', 'inference_api_url'\\], "
            "you must only set one per instance.",
            id='openmetrics and inference',
        ),
        pytest.param(
            {"openmetrics_endpoint", "management_api_url"},
            "Too many endpoints configured for this instance: \\['openmetrics_endpoint', 'management_api_url'\\], "
            "you must only set one per instance.",
            id='openmetrics and management',
        ),
        pytest.param(
            {"inference_api_url", "management_api_url"},
            "Too many endpoints configured for this instance: \\['inference_api_url', 'management_api_url'\\], "
            "you must only set one per instance.",
            id='inference and management',
        ),
        pytest.param(
            {"inference_api_url", "management_api_url", "openmetrics_endpoint"},
            "Too many endpoints configured for this instance: \\['openmetrics_endpoint', 'inference_api_url', "
            "'management_api_url'\\], you must only set one per instance.",
            id='inference, management and openmetrics',
        ),
    ],
)
def test_invalid_configs(check, instance, error_message):
    with pytest.raises(ConfigurationError, match=error_message):
        check(instance)
