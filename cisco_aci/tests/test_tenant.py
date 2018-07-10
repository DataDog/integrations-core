# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import pytest
import logging
import simplejson as json
from requests import Session, Response

from datadog_checks.cisco_aci.api import SessionWrapper, Api
from datadog_checks.cisco_aci.tenant import Tenant
from datadog_checks.cisco_aci import CiscoACICheck

from datadog_checks.utils.containers import hash_mutable

from common import FIXTURE_LIST_FILE_MAP


log = logging.getLogger('test_cisco_aci')

CHECK_NAME = 'cisco_aci'

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
TENANT_FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'tenant')

USERNAME = 'datadog'
PASSWORD = 'datadog'
ACI_URL = 'https://datadoghq.com'
ACI_URLS = [ACI_URL]
CONFIG = {
    'aci_urls': ACI_URLS,
    'username': USERNAME,
    'pwd': PASSWORD,
    'tenant': [
        'DataDog',
    ],
    "tags": ["project:cisco_aci"],
}


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


class FakeSess(SessionWrapper):
    """ This mock:
     1. Takes the requested path and replace all special characters to underscore
     2. Fetch the corresponding hash from FIXTURE_LIST_FILE_MAP
     3. Returns the corresponding file content
     """
    def make_request(self, path):
        mock_path = path.replace('/', '_')
        mock_path = mock_path.replace('?', '_')
        mock_path = mock_path.replace('&', '_')
        mock_path = mock_path.replace('=', '_')
        mock_path = mock_path.replace(',', '_')
        mock_path = mock_path.replace('-', '_')
        mock_path = mock_path.replace('.', '_')
        mock_path = mock_path.replace('"', '_')
        mock_path = mock_path.replace('(', '_')
        mock_path = mock_path.replace(')', '_')
        mock_path = mock_path.replace('[', '_')
        mock_path = mock_path.replace(']', '_')
        mock_path = mock_path.replace('|', '_')
        try:
            mock_path = FIXTURE_LIST_FILE_MAP[mock_path]

            mock_path = os.path.join(TENANT_FIXTURES_DIR, mock_path)
            mock_path += '.txt'

            log.info(os.listdir(TENANT_FIXTURES_DIR))

            with open(mock_path, 'r') as f:
                return json.loads(f.read())
        except Exception:
            return {"imdata": []}


def mock_send(prepped_request, **kwargs):
    if prepped_request.path_url == '/api/aaaLogin.xml':
        cookie_path = os.path.join(FIXTURES_DIR, 'login_cookie.txt')
        response_path = os.path.join(FIXTURES_DIR, 'login.txt')
        response = Response()
        with open(cookie_path, 'r') as f:
            response.cookies = {'APIC-cookie': f.read()}
        with open(response_path, 'r') as f:
            response.raw = f.read()

    return response


@pytest.fixture
def session_mock():
    session = Session()
    setattr(session, 'send', mock_send)
    fake_session_wrapper = FakeSess(ACI_URL, session, 'cookie')

    return fake_session_wrapper


def test_tenant_end_to_end(aggregator, session_mock):
    check = CiscoACICheck(CHECK_NAME, {}, {})
    api = Api(ACI_URLS, USERNAME, PASSWORD, log=check.log, sessions=[session_mock])
    api._refresh_sessions = False
    check._api_cache[hash_mutable(CONFIG)] = api

    check.check(CONFIG)

    tags = ['project:cisco_aci', 'tenant:DataDog']
    # TODO pretty much everything is 0 and without hostname??
    metric_name = 'cisco_aci.tenant.ingress_bytes.multicast.rate'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.egress_bytes.multicast.rate'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')
    
    metric_name = 'cisco_aci.tenant.ingress_pkts.multicast.rate'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')
    metric_name = 'cisco_aci.tenant.health'
    aggregator.assert_metric(metric_name, value=99.0, tags=tags, hostname='')
    
    metric_name = 'cisco_aci.tenant.overall_health'
    aggregator.assert_metric(metric_name, value=99.0, tags=tags, hostname='')

    metric_name = 'cisco_aci.tenant.egress_pkts.unicast.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')
    
    metric_name = 'cisco_aci.tenant.egress_pkts.unicast.rate'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')
    
    metric_name = 'cisco_aci.tenant.application.fault_counter'
    aggregator.assert_metric(metric_name, value=0.0, tags=['application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['application:DtDg-test-AP'] + tags, hostname='')
    
    metric_name = 'cisco_aci.tenant.fault_counter'
    aggregator.assert_metric(metric_name, value=4.0, tags=tags, hostname='')

    metric_name = 'cisco_aci.tenant.ingress_bytes.flood.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.ingress_pkts.unicast.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.egress_bytes.unicast.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.egress_pkts.multicast.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.ingress_pkts.flood.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.egress_bytes.unicast.rate'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.egress_bytes.multicast.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.ingress_bytes.unicast.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.ingress_pkts.drop.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.capacity.apic.fabric_node.utilized'
    aggregator.assert_metric(metric_name, value=0.0, tags=['project:cisco_aci', 'cisco'], hostname='') # TODO are tags valid here? valie is 2.0 in test_cisco

    metric_name = 'cisco_aci.tenant.ingress_pkts.multicast.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.egress_pkts.multicast.rate'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.ingress_bytes.drop.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.ingress_bytes.unicast.rate'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.ingress_bytes.multicast.cum'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    metric_name = 'cisco_aci.tenant.ingress_pkts.unicast.rate'
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Pay',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-MiscAppVMs',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Inv',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ord',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Ecomm',
                                                           'application:DtDg-AP1-EcommerceApp'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti2',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jetty_Controller',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:DtDg-Jeti1',
                                                           'application:DtDg-AP2-Jeti'] + tags, hostname='')
    aggregator.assert_metric(metric_name, value=0.0, tags=['endpoint_group:Test-EPG',
                                                           'application:DtDg-test-AP'] + tags, hostname='')

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
