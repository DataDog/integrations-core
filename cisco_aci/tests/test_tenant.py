# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import logging

# import simplejson as json

from datadog_checks.cisco_aci import CiscoACICheck
from datadog_checks.cisco_aci.tenant import Tenant

from datadog_checks.utils.containers import hash_mutable

log = logging.getLogger('test_cisco_aci')


CHECK_NAME = 'cisco_aci'


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


class ApiMock:
    def __init__(self):
        pass

    def get_apps(self, tenant):
        return [{"fvAp": {"attributes": {"name": "app1"}}}]

    def get_app_stats(self, tenant, app):
        return [{"15min": {"attributes": {"attr": "1"}}},
                {"index": {"attributes": {"attr": "2"}}},
                {"other": {"attributes": {"attr": "3"}}}]

    def get_epgs(self, tenant, app):
        return [{"fvAEPg": {"attributes": {"name": "app1"}}}]

    def get_epg_stats(self, tenant, app, epg):
        return [{"15min": {"attributes": {"attr": "1"}}},
                {"index": {"attributes": {"attr": "2"}}},
                {"other": {"attributes": {"attr": "3"}}}]

    def get_tenant_stats(self, tenant):
        return [{"15min": {"attributes": {"attr": "1"}}},
                {"index": {"attributes": {"attr": "2"}}},
                {"other": {"attributes": {"attr": "3"}}}]

    def get_tenant_events(self, tenant, page=0, page_size=15):
        return []

    def get_epg_meta(self, tenant, app, epg):
        return [{"fvCEp": {"attributes": {"ip": "ip1", "mac": "mac1", "encap": "encap1"}}}]

    def get_eth_list_for_epg(self, tenant, app, epg):
        return []


def test_no_tenant(aggregator):
    api = ApiMock()
    check = CiscoACICheck(CHECK_NAME, {}, {})
    api._refresh_sessions = False
    check._api_cache[hash_mutable(hash_mutable({}))] = api
    tenant = Tenant(check, api, {}, None)
    tenant.collect()

    assert len(aggregator._metrics.items()) == 0


# def test_one_tenant(aggregator):
#     config = {
#         'tenant': [
#             'DataDog',
#         ]}
#     api = ApiMock()
#     check = CiscoACICheck(CHECK_NAME, {}, {})
#     api._refresh_sessions = False
#     check._api_cache[hash_mutable(hash_mutable(config))] = api
#     check.tagger.api = api
#     tenant = Tenant(check, api, config, None)
#     tenant.collect()
#
#     for m in aggregator._metrics.items():
#         print(m)
#
#     assert len(aggregator._metrics.items()) == 1
