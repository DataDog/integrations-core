# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import EXPECTED_TAGS

pytestmark = pytest.mark.e2e


def test_mock_data(dd_agent_check, datadog_agent, instance):
    instance['metric_groups'] = [
        'snowflake.billing',
        'snowflake.logins',
        'snowflake.query',
        'snowflake.storage',
        'snowflake.storage.database',
    ]
    aggregator = dd_agent_check(instance, rate=True)

    aggregator.assert_metric('snowflake.storage.storage_bytes.total', value=0.0, tags=EXPECTED_TAGS)
    aggregator.assert_metric('snowflake.storage.stage_bytes.total', value=1206.0, tags=EXPECTED_TAGS)
    aggregator.assert_metric('snowflake.storage.failsafe_bytes.total', value=19.2, tags=EXPECTED_TAGS)

    aggregator.assert_metric(
        'snowflake.storage.database.storage_bytes', value=133.0, tags=EXPECTED_TAGS + ['database:SNOWFLAKE_DB']
    )
    aggregator.assert_metric(
        'snowflake.storage.database.failsafe_bytes', value=9.1, tags=EXPECTED_TAGS + ['database:SNOWFLAKE_DB']
    )

    aggregator.assert_metric(
        'snowflake.billing.cloud_service.sum',
        tags=EXPECTED_TAGS + ['service_type:WAREHOUSE_METERING', 'snowflake_service:COMPUTE_WH'],
    )
    aggregator.assert_metric(
        'snowflake.billing.cloud_service.avg',
        tags=EXPECTED_TAGS + ['service_type:WAREHOUSE_METERING', 'snowflake_service:COMPUTE_WH'],
    )
    aggregator.assert_metric('snowflake.billing.total_credit.sum')
    aggregator.assert_metric('snowflake.billing.total_credit.avg')
    aggregator.assert_metric('snowflake.billing.virtual_warehouse.sum')
    aggregator.assert_metric('snowflake.billing.virtual_warehouse.avg')

    aggregator.assert_metric(
        'snowflake.billing.warehouse.cloud_service.avg', tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH']
    )
    aggregator.assert_metric(
        'snowflake.billing.warehouse.total_credit.avg', tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH']
    )
    aggregator.assert_metric(
        'snowflake.billing.warehouse.virtual_warehouse.avg', tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH']
    )
    aggregator.assert_metric(
        'snowflake.billing.warehouse.cloud_service.sum', tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH']
    )
    aggregator.assert_metric(
        'snowflake.billing.warehouse.total_credit.sum', tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH']
    )
    aggregator.assert_metric(
        'snowflake.billing.warehouse.virtual_warehouse.sum', tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH']
    )

    aggregator.assert_metric('snowflake.logins.fail.count', tags=EXPECTED_TAGS + ['client_type:SNOWFLAKE_UI'])
    aggregator.assert_metric('snowflake.logins.success.count', tags=EXPECTED_TAGS + ['client_type:SNOWFLAKE_UI'])
    aggregator.assert_metric('snowflake.logins.total', tags=EXPECTED_TAGS + ['client_type:SNOWFLAKE_UI'])
    aggregator.assert_metric('snowflake.logins.fail.count', tags=EXPECTED_TAGS + ['client_type:PYTHON_DRIVER'])
    aggregator.assert_metric('snowflake.logins.success.count', tags=EXPECTED_TAGS + ['client_type:PYTHON_DRIVER'])
    aggregator.assert_metric('snowflake.logins.total', tags=EXPECTED_TAGS + ['client_type:PYTHON_DRIVER'])

    aggregator.assert_metric(
        'snowflake.query.executed', value=0.000446667, tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH']
    )
    aggregator.assert_metric('snowflake.query.queued_overload', value=0, tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH'])
    aggregator.assert_metric('snowflake.query.queued_provision', value=0, tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH'])
    aggregator.assert_metric('snowflake.query.blocked', value=0, tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH'])

    aggregator.assert_metric(
        'snowflake.query.execution_time',
        value=4.333333,
        tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH', 'database:SNOWFLAKE', 'schema:None', 'query_type:USE'],
    )
    aggregator.assert_metric(
        'snowflake.query.compilation_time',
        value=24.555556,
        tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH', 'database:SNOWFLAKE', 'schema:None', 'query_type:USE'],
    )
    aggregator.assert_metric(
        'snowflake.query.bytes_scanned',
        value=0,
        tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH', 'database:SNOWFLAKE', 'schema:None', 'query_type:USE'],
    )
    aggregator.assert_metric(
        'snowflake.query.bytes_written',
        value=0,
        tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH', 'database:SNOWFLAKE', 'schema:None', 'query_type:USE'],
    )
    aggregator.assert_metric(
        'snowflake.query.bytes_deleted',
        value=0,
        tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH', 'database:SNOWFLAKE', 'schema:None', 'query_type:USE'],
    )
    aggregator.assert_metric(
        'snowflake.query.bytes_spilled.local',
        value=0,
        tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH', 'database:SNOWFLAKE', 'schema:None', 'query_type:USE'],
    )
    aggregator.assert_metric(
        'snowflake.query.bytes_spilled.remote',
        value=0,
        tags=EXPECTED_TAGS + ['warehouse:COMPUTE_WH', 'database:SNOWFLAKE', 'schema:None', 'query_type:USE'],
    )

    datadog_agent.assert_metadata(
        'snowflake',
        {
            'version.major': '4',
            'version.minor': '30',
            'version.patch': '2',
            'version.raw': '4.30.2',
            'version.scheme': 'semver',
        },
    )
