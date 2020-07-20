# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.couch import CouchDb, errors

from . import common

pytestmark = pytest.mark.skipif(common.COUCH_MAJOR_VERSION != 1, reason='Test for version Couch v1')


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_couch(aggregator, check, instance):
    check.check(instance)
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
def test_bad_config(aggregator, check, instance):
    """
    Test the check with various bogus instances
    """
    with pytest.raises(errors.BadConfigError):
        # `server` is missing from the instance
        check.check({})

    with pytest.raises(errors.ConnectionError):
        # the server instance is invalid
        check.check(common.BAD_CONFIG)
        aggregator.assert_service_check(
            CouchDb.SERVICE_CHECK_NAME, status=CouchDb.CRITICAL, tags=common.BAD_CONFIG_TAGS, count=1
        )

    check.get = mock.MagicMock(return_value={'version': '0.1.0'})
    with pytest.raises(errors.BadVersionError):
        # the server has an unsupported version
        check.check(common.BAD_CONFIG)
        aggregator.assert_service_check(
            CouchDb.SERVICE_CHECK_NAME, status=CouchDb.CRITICAL, tags=common.BAD_CONFIG_TAGS, count=1
        )


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize('param_name', ["db_whitelist", "db_include"])
def test_couch_inclusion(aggregator, check, instance, param_name):
    DB_INCLUDE = ["_users"]
    instance[param_name] = DB_INCLUDE
    check.check(instance)

    for db_name in common.DB_NAMES:
        expected_tags = common.BASIC_CONFIG_TAGS + ["db:{}".format(db_name), "device:{}".format(db_name)]
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
    check.check(instance)

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
    check.check(instance)
    for gauge in common.CHECK_GAUGES:
        aggregator.assert_metric(gauge, count=1)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_config_tags(aggregator, check, instance):
    TEST_TAG = "test_tag"
    instance["tags"] = [TEST_TAG]
    check.check(instance)

    for gauge in common.CHECK_GAUGES:
        aggregator.assert_metric_has_tag(gauge, TEST_TAG)

    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, tags=common.BASIC_CONFIG_TAGS + [TEST_TAG])
