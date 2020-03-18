# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.cisco_aci import CiscoACICheck
from datadog_checks.cisco_aci.api import Api
from datadog_checks.cisco_aci.tenant import Tenant
from datadog_checks.base.utils.containers import hash_mutable

from . import common


class ApiMock:
    def __init__(self):
        pass

    def get_apps(self, tenant):
        return [{"fvAp": {"attributes": {"name": "app1"}}}]

    def get_app_stats(self, tenant, app):
        return [
            {"15min": {"attributes": {"attr": "1"}}},
            {"index": {"attributes": {"attr": "2"}}},
            {"other": {"attributes": {"attr": "3"}}},
        ]

    def get_epgs(self, tenant, app):
        return [{"fvAEPg": {"attributes": {"name": "app1"}}}]

    def get_epg_stats(self, tenant, app, epg):
        return [
            {"15min": {"attributes": {"attr": "1"}}},
            {"index": {"attributes": {"attr": "2"}}},
            {"other": {"attributes": {"attr": "3"}}},
        ]

    def get_tenant_stats(self, tenant):
        return [
            {"15min": {"attributes": {"attr": "1"}}},
            {"index": {"attributes": {"attr": "2"}}},
            {"other": {"attributes": {"attr": "3"}}},
        ]

    def get_tenant_events(self, tenant, page=0, page_size=15):
        return []

    def get_epg_meta(self, tenant, app, epg):
        return [{"fvCEp": {"attributes": {"ip": "ip1", "mac": "mac1", "encap": "encap1"}}}]

    def get_eth_list_for_epg(self, tenant, app, epg):
        return []


def test_no_tenant(aggregator):
    api = ApiMock()
    check = CiscoACICheck(common.CHECK_NAME, {}, {})
    api._refresh_sessions = False
    check._api_cache[hash_mutable(hash_mutable({}))] = api
    tenant = Tenant(check, api, {}, None)
    tenant.collect()

    assert len(aggregator._metrics.items()) == 0


def test_tenant_mocked(aggregator):
    check = CiscoACICheck(common.CHECK_NAME, {}, {})
    api = Api(common.ACI_URLS, check.http, common.USERNAME, password=common.PASSWORD, log=check.log)
    api.wrapper_factory = common.FakeTenantSessionWrapper
    check._api_cache[hash_mutable(common.CONFIG_WITH_TAGS)] = api

    check.check(common.CONFIG_WITH_TAGS)

    tags = ['project:cisco_aci', 'tenant:DataDog']
    metric_name = 'cisco_aci.tenant.ingress_bytes.multicast.rate'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.egress_bytes.multicast.rate'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.ingress_pkts.multicast.rate'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.health'
    aggregator.assert_metric(metric_name, value=99.0, tags=tags, hostname='')

    metric_name = 'cisco_aci.tenant.overall_health'
    aggregator.assert_metric(metric_name, value=99.0, tags=tags, hostname='')

    metric_name = 'cisco_aci.tenant.egress_pkts.unicast.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.egress_pkts.unicast.rate'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.application.fault_counter'
    aggregator.assert_metric(metric_name, value=0.0, tags=['application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.fault_counter'
    aggregator.assert_metric(metric_name, value=4.0, tags=tags, hostname='')

    metric_name = 'cisco_aci.tenant.ingress_bytes.flood.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.ingress_pkts.unicast.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.egress_bytes.unicast.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.egress_pkts.multicast.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.ingress_pkts.flood.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.egress_bytes.unicast.rate'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.egress_bytes.multicast.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.ingress_bytes.unicast.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.ingress_pkts.drop.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.capacity.apic.fabric_node.utilized'
    aggregator.assert_metric(metric_name, value=0.0, tags=['project:cisco_aci', 'cisco'], hostname='')

    metric_name = 'cisco_aci.tenant.ingress_pkts.multicast.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.egress_pkts.multicast.rate'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.ingress_bytes.drop.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.ingress_bytes.unicast.rate'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.ingress_bytes.multicast.cum'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    metric_name = 'cisco_aci.tenant.ingress_pkts.unicast.rate'
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Pay', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-MiscAppVMs', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Inv', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ord', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Ecomm', 'application:DtDg-AP1-EcommerceApp'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name,
        value=0.0,
        tags=['endpoint_group:DtDg-Jetty_Controller', 'application:DtDg-AP2-Jeti'] + tags,
        hostname='',
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1', 'application:DtDg-AP2-Jeti'] + tags, hostname=''
    )
    aggregator.assert_metric(
        metric_name, value=0.0, tags=['endpoint_group:Test-EPG', 'application:DtDg-test-AP'] + tags, hostname=''
    )

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
