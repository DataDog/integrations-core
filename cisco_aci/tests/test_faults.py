# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.utils.containers import hash_mutable
from datadog_checks.cisco_aci import CiscoACICheck
from datadog_checks.cisco_aci.api import Api

from . import common
from .fixtures.faults import EXPECTED_FAULT_LOGS


def test_faults_mocked(aggregator, datadog_agent):
    check = CiscoACICheck(common.CHECK_NAME, {}, [common.CONFIG_WITH_TAGS])
    api = Api(common.ACI_URLS, check.http, common.USERNAME, password=common.PASSWORD, log=check.log)
    api.wrapper_factory = common.FakeFaultsSessionWrapper
    check._api_cache[hash_mutable(common.CONFIG_WITH_TAGS)] = api

    check.check({})
    check.check({})  # Run twice to exercise the max_timestamp logic
    datadog_agent.assert_logs(check.check_id, EXPECTED_FAULT_LOGS)


def test_faults_ndm_metadata_false_mocked(aggregator, datadog_agent):
    config_without_ndm = common.CONFIG_WITH_TAGS.copy()
    config_without_ndm['send_ndm_metadata'] = False
    check = CiscoACICheck(common.CHECK_NAME, {}, [config_without_ndm])
    api = Api(common.ACI_URLS, check.http, common.USERNAME, password=common.PASSWORD, log=check.log)
    api.wrapper_factory = common.FakeFaultsSessionWrapper
    check._api_cache[hash_mutable(config_without_ndm)] = api

    check.check({})
    datadog_agent.assert_logs(check.check_id, [])
