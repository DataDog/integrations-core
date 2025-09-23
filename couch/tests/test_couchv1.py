# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.couch import CouchDb

from . import common

pytestmark = pytest.mark.skipif(common.COUCH_MAJOR_VERSION != 1, reason='Test for version Couch v1')


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_couch(aggregator, check, dd_run_check):
    dd_run_check(check)
    _assert_check(aggregator, assert_device_tag=True)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)
    _assert_check(aggregator, assert_device_tag=False)


def _assert_check(aggregator, assert_device_tag):
    # Metrics should have been emitted for any publicly readable databases.
    for db_name in common.DB_NAMES:
        for gauge in common.CHECK_GAUGES:
            expected_tags = common.BASIC_CONFIG_TAGS + ["db:{}".format(db_name)]
            if assert_device_tag:
                expected_tags.append("device:{}".format(db_name))
            aggregator.assert_metric(gauge, tags=expected_tags, count=1)

    # Check global metrics
    for gauge in common.GLOBAL_GAUGES:
        aggregator.assert_metric(gauge, tags=common.BASIC_CONFIG_TAGS, at_least=0)

    # 2 service checks: 1 per DB + 1 to get the version
    aggregator.assert_service_check(
        CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=common.BASIC_CONFIG_TAGS, count=2
    )


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize('param_name', ["db_whitelist", "db_include"])
def test_couch_inclusion(aggregator, check, instance, param_name):
    DB_INCLUDE = ["_users"]
    instance[param_name] = DB_INCLUDE
    check.instance = instance
    check.check({})

    for db_name in common.DB_NAMES:
        expected_tags = ["db:{}".format(db_name), "device:{}".format(db_name)] + common.BASIC_CONFIG_TAGS
        for gauge in common.CHECK_GAUGES:
            if db_name in DB_INCLUDE:
                aggregator.assert_metric(gauge, tags=expected_tags, count=1)
            else:
                aggregator.assert_metric(gauge, tags=expected_tags, count=0)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize('param_name', ["db_blacklist", "db_exclude"])
def test_couch_exclusion(aggregator, check, instance, param_name):
    DB_EXCLUDE = ["_replicator"]
    instance[param_name] = DB_EXCLUDE
    check.instance = instance
    check.check({})

    for db_name in common.DB_NAMES:
        expected_tags = common.BASIC_CONFIG_TAGS + ["db:{}".format(db_name), "device:{}".format(db_name)]
        for gauge in common.CHECK_GAUGES:
            if db_name in DB_EXCLUDE:
                aggregator.assert_metric(gauge, tags=expected_tags, count=0)
            else:
                aggregator.assert_metric(gauge, tags=expected_tags, count=1)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_only_max_nodes_are_scanned(aggregator, check, instance):
    instance["max_dbs_per_check"] = 1
    check.instance = instance
    check.check({})
    for gauge in common.CHECK_GAUGES:
        aggregator.assert_metric(gauge, count=1)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_config_tags(aggregator, check, instance):
    TEST_TAG = "test_tag"
    instance["tags"] = [TEST_TAG]
    check.instance = instance
    check.check({})

    for gauge in common.CHECK_GAUGES:
        aggregator.assert_metric_has_tag(gauge, TEST_TAG)

    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, tags=common.BASIC_CONFIG_TAGS + [TEST_TAG])


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize('enable_per_db_metrics', [True, False])
def test_per_db_metrics(aggregator, check, enable_per_db_metrics):
    config = common.BASIC_CONFIG.copy()
    config["enable_per_db_metrics"] = enable_per_db_metrics

    check.instance = config
    check.check({})

    if enable_per_db_metrics:
        aggregator.assert_metric("couchdb.by_db.doc_count", at_least=1)
    else:
        aggregator.assert_metric("couchdb.by_db.doc_count", count=0)
