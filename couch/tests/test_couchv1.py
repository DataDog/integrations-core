# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.couch import CouchDb
import common

pytestmark = pytest.mark.v1


def test_couch(aggregator, spin_up_couchv1):

    check = CouchDb(common.CHECK_NAME, {}, {})
    check.check(common.BASIC_CONFIG)

    # Metrics should have been emitted for any publicly readable databases.
    for db_name in common.DB_NAMES:
        for gauge in common.CHECK_GAUGES:
            expected_tags = common.BASIC_CONFIG_TAGS + [
                "db:{}".format(db_name),
                "device:{}".format(db_name)
            ]
            aggregator.assert_metric(gauge, tags=expected_tags, count=1)

    # Check global metrics
    for gauge in common.GLOBAL_GAUGES:
        aggregator.assert_metric(gauge, tags=common.BASIC_CONFIG_TAGS, at_least=0)

    # 2 service checks: 1 per DB + 1 to get the version
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK,
                                    tags=common.BASIC_CONFIG_TAGS, count=2)


def test_bad_config(aggregator):

    check = CouchDb(common.CHECK_NAME, {}, {})
    raised = False

    try:
        print(common.BAD_CONFIG)
        check.check(common.BAD_CONFIG)
    except Exception:
        raised = True

    assert raised
    print(aggregator._service_checks)
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.CRITICAL,
                                    tags=common.BAD_CONFIG_TAGS, count=1)


def test_couch_whitelist(aggregator, spin_up_couchv1):
    check = CouchDb(common.CHECK_NAME, {}, {})

    DB_WHITELIST = ["_users"]
    config = deepcopy(common.BASIC_CONFIG)
    config["db_whitelist"] = DB_WHITELIST
    check.check(config)

    for db_name in common.DB_NAMES:
        expected_tags = common.BASIC_CONFIG_TAGS + [
            "db:{}".format(db_name),
            "device:{}".format(db_name)
        ]
        for gauge in common.CHECK_GAUGES:
            if db_name in DB_WHITELIST:
                aggregator.assert_metric(gauge, tags=expected_tags, count=1)
            else:
                aggregator.assert_metric(gauge, tags=expected_tags, count=0)


def test_couch_blacklist(aggregator, spin_up_couchv1):
    check = CouchDb(common.CHECK_NAME, {}, {})

    DB_BLACKLIST = ["_replicator"]
    config = deepcopy(common.BASIC_CONFIG)
    config["db_blacklist"] = DB_BLACKLIST
    check.check(config)

    for db_name in common.DB_NAMES:
        expected_tags = common.BASIC_CONFIG_TAGS + [
            "db:{}".format(db_name),
            "device:{}".format(db_name)
        ]
        for gauge in common.CHECK_GAUGES:
            if db_name in DB_BLACKLIST:
                aggregator.assert_metric(gauge, tags=expected_tags, count=0)
            else:
                aggregator.assert_metric(gauge, tags=expected_tags, count=1)


def test_only_max_nodes_are_scanned(aggregator, spin_up_couchv1):
    check = CouchDb(common.CHECK_NAME, {}, {})

    config = deepcopy(common.BASIC_CONFIG)
    config["max_dbs_per_check"] = 1
    check.check(config)
    print(aggregator._metrics)
    for gauge in common.CHECK_GAUGES:
        aggregator.assert_metric(gauge, count=1)


def test_config_tags(aggregator, spin_up_couchv1):
    check = CouchDb(common.CHECK_NAME, {}, {})

    TEST_TAG = "test_tag"
    config = deepcopy(common.BASIC_CONFIG)
    config["tags"] = [TEST_TAG]
    check.check(config)

    for gauge in common.CHECK_GAUGES:
        aggregator.assert_metric_has_tag(gauge, TEST_TAG)

    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, tags=common.BASIC_CONFIG_TAGS + [TEST_TAG])
