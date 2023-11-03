# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.mysql import MySql

from . import common


@pytest.fixture
def dbm_instance(instance_complex):
    instance_complex['dbm'] = True
    instance_complex['query_samples'] = {'enabled': False}
    instance_complex['query_metrics'] = {'enabled': False}
    instance_complex['query_activity'] = {'enabled': False}
    instance_complex['collect_settings'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    return instance_complex


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_collect_mysql_settings(aggregator, dbm_instance, dd_run_check):
    # test to make sure we continue to support the old key
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    dd_run_check(mysql_check)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'mysql_variables'), None)
    assert event is not None
    assert event['host'] == "stubbed.hostname"
    assert event['dbms'] == "mysql"
    assert len(event["metadata"]) > 0
