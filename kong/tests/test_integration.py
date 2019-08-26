import pytest

from datadog_checks.kong import Kong

from . import common


@pytest.mark.usefixtures('dd_environment')
def test_connection_failure(aggregator, check):
    with pytest.raises(Exception):
        check.check(common.BAD_CONFIG)
    aggregator.assert_service_check(
        'kong.can_connect', status=Kong.CRITICAL, tags=['kong_host:localhost', 'kong_port:1111'], count=1
    )

    aggregator.all_metrics_asserted()
