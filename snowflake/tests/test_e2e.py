# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import EXPECTED_TAGS

pytestmark = pytest.mark.e2e


def test_account_usage_mock_data(dd_agent_check, instance):
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


def test_org_usage_mock_data(dd_agent_check, instance):
    instance['schema'] = 'ORGANIZATION_USAGE'
    instance['metric_groups'] = [
        'snowflake.organization.contracts',
        'snowflake.organization.credit',
        'snowflake.organization.currency',
        'snowflake.organization.warehouse',
        'snowflake.organization.storage',
        'snowflake.organization.balance',
        'snowflake.organization.rate',
        'snowflake.organization.data_transfer',
    ]
    aggregator = dd_agent_check(instance, rate=True)

    currency_tags = [
        'billing_account:test',
        'service_level:Standard',
        'usage_type:Compute',
        'currency:USD',
    ]
    aggregator.assert_metric('snowflake.organization.currency.usage', value=0.4, tags=EXPECTED_TAGS + currency_tags)
    aggregator.assert_metric(
        'snowflake.organization.currency.usage_in_currency', value=0.7, tags=EXPECTED_TAGS + currency_tags
    )

    credit_usage_tags = [
        'billing_account:account_name',
        'service_type:Standard',
    ]
    aggregator.assert_metric(
        'snowflake.organization.credit.virtual_warehouse.sum', value=300, tags=EXPECTED_TAGS + credit_usage_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.credit.virtual_warehouse.avg', value=3.4, tags=EXPECTED_TAGS + credit_usage_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.credit.cloud_service.sum', value=902.49003, tags=EXPECTED_TAGS + credit_usage_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.credit.cloud_service.avg', value=4.9227, tags=EXPECTED_TAGS + credit_usage_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.credit.cloud_service_adjustment.sum',
        value=212.43,
        tags=EXPECTED_TAGS + credit_usage_tags,
    )
    aggregator.assert_metric(
        'snowflake.organization.credit.cloud_service_adjustment.avg', value=34.7, tags=EXPECTED_TAGS + credit_usage_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.credit.total_credit.sum', value=342.8321, tags=EXPECTED_TAGS + credit_usage_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.credit.total_credit.avg', value=1.7, tags=EXPECTED_TAGS + credit_usage_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.credit.total_credits_billed.sum', value=21.02, tags=EXPECTED_TAGS + credit_usage_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.credit.total_credits_billed.avg', value=2.9, tags=EXPECTED_TAGS + credit_usage_tags
    )

    contract_tags = [
        'contract_number:4',
        'contract_item:Free Usage',
        'currency:USD',
    ]
    aggregator.assert_metric('snowflake.organization.contract.amount', value=23, tags=EXPECTED_TAGS + contract_tags)

    warehouse_tags = [
        'warehouse:test',
        'billing_account:account_name',
    ]
    aggregator.assert_metric(
        'snowflake.organization.warehouse.virtual_warehouse.sum', value=300, tags=EXPECTED_TAGS + warehouse_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.warehouse.virtual_warehouse.avg', value=3.4, tags=EXPECTED_TAGS + warehouse_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.warehouse.cloud_service.sum', value=902.49003, tags=EXPECTED_TAGS + warehouse_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.warehouse.cloud_service.avg', value=4.9227, tags=EXPECTED_TAGS + warehouse_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.warehouse.total_credit.sum', value=212.43, tags=EXPECTED_TAGS + warehouse_tags
    )
    aggregator.assert_metric(
        'snowflake.organization.warehouse.total_credit.avg', value=34.7, tags=EXPECTED_TAGS + warehouse_tags
    )

    storage_tags = [
        'billing_account:account_name',
    ]
    aggregator.assert_metric(
        'snowflake.organization.storage.average_bytes', value=4510, tags=EXPECTED_TAGS + storage_tags
    )
    aggregator.assert_metric('snowflake.organization.storage.credits', value=349, tags=EXPECTED_TAGS + storage_tags)

    balance_tags = ['contract_number:4', 'currency:USD']
    aggregator.assert_metric(
        'snowflake.organization.balance.free_usage', value=23410, tags=EXPECTED_TAGS + balance_tags
    )
    aggregator.assert_metric('snowflake.organization.balance.capacity', value=814349, tags=EXPECTED_TAGS + balance_tags)
    aggregator.assert_metric(
        'snowflake.organization.balance.on_demand_consumption', value=-35435, tags=EXPECTED_TAGS + balance_tags
    )
    aggregator.assert_metric('snowflake.organization.balance.rollover', value=455435, tags=EXPECTED_TAGS + balance_tags)

    data_transfer_tags = ['billing_account:test_account', 'source_cloud:AWS', 'target_cloud:GCP', 'transfer_type:COPY']
    aggregator.assert_metric(
        'snowflake.organization.data_transfer.bytes_transferred', value=13.56, tags=EXPECTED_TAGS + data_transfer_tags
    )

    rate_tags = [
        'contract_number:3',
        'billing_account:test_account',
        'usage_type:usage',
        'service_type:service',
        'currency:USD',
    ]
    aggregator.assert_metric('snowflake.organization.rate.effective_rate', value=312, tags=EXPECTED_TAGS + rate_tags)
