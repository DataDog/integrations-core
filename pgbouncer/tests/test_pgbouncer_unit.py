# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.pgbouncer import PgBouncer


@pytest.mark.unit
def test_critical_service_check(instance, aggregator):
    instance['port'] = '123'  # Bad port
    check = PgBouncer('pgbouncer', {}, [instance])
    with pytest.raises(Exception):
        check.check(instance)
    aggregator.assert_service_check(PgBouncer.SERVICE_CHECK_NAME, status=PgBouncer.CRITICAL)


@pytest.mark.unit
def test_config_missing_host(instance):
    with pytest.raises(ConfigurationError):
        del instance['host']
        PgBouncer('pgbouncer', {}, [instance])


@pytest.mark.unit
def test_config_missing_user(instance):
    with pytest.raises(ConfigurationError):
        del instance['username']
        PgBouncer('pgbouncer', {}, [instance])


# Not sure how to get the logger output
# @pytest.mark.unit
# def test_fail_collect_tests(instance):
#     check = PgBouncer('pgbouncer', {}, [instance])
#
#     mock_cursor = mock.MagicMock()
#     mock_cursor.execute = mock.MagicMock(side_effect=ConfigurationError)  # catch error unrelated to postgres
#     db = mock.MagicMock(return_value=mock_cursor)
#
#     check._collect_stats(db)
#     # check that `Not all metrics may be available` was logged
