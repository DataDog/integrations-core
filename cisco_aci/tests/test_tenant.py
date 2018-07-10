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

log = logging.getLogger('test_cisco_aci')

CHECK_NAME = 'cisco_aci'

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')

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
    #tenant uses get_apps, get_epgs, get_app_stats, get_epg_stats, get_tenant_stats, get_tenant_events
    def make_request(self, path):
        FIXTURE_LIST_FILE_MAP = {
            # Api.get_apps
            '_api_mo_uni_tn_DataDog_json_query_target_subtree_target_subtree_class_fvAp': "4efe80304d50330f5ed0f79252ef0a84",
            # Api.get_epgs
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_json_query_target_subtree_target_subtree_class_fvAEPg': "d98210e57060ed7285a4fa7434c53ff1",
            '_api_mo_uni_tn_DataDog_ap_DtDg_test_AP_json_query_target_subtree_target_subtree_class_fvAEPg': "4b07d389b109401afcc2c42bdca0f2b2",
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_json_query_target_subtree_target_subtree_class_fvAEPg': "43410607b378cfa340146247a8b422b9",
            # Api.get_app_stats
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_json_rsp_subtree_include_stats_no_scoped': "363e27e35a42bb987c121709284b529f",
            '_api_mo_uni_tn_DataDog_ap_DtDg_test_AP_json_rsp_subtree_include_stats_no_scoped': "1c7d7ebf0b75333689662feb19f63ede",
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_json_rsp_subtree_include_stats_no_scoped': "10b987e92abaab8d843e6bee5ab6aef0",
            # Api.get_epg_stats
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jeti1_json_rsp_subtree_include_stats_no_scoped': "f44f8e9a9afe5d47c8b27d06b6458200",
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jeti2_json_rsp_subtree_include_stats_no_scoped': "d4efb7c9b80929991dd91850d9ddceef",
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_MiscAppVMs_json_rsp_subtree_include_stats_no_scoped': "288a353bc9fed8f571d78076cb1585ae",
            '_api_mo_uni_tn_DataDog_ap_DtDg_test_AP_epg_Test_EPG_json_rsp_subtree_include_stats_no_scoped': "3f8f3374048d7b5b3a38566765f35cc2",
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Inv_json_rsp_subtree_include_stats_no_scoped': "eb4804e1e68e00353c89b13b56b9d7b9",
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Ord_json_rsp_subtree_include_stats_no_scoped': "af6ca37b21581b58b9901e23dd02cae9",
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Ecomm_json_rsp_subtree_include_stats_no_scoped': "f929ec691d62a0d70a12e51fc18b4321",
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jetty_Controller_json_rsp_subtree_include_stats_no_scoped': "7034a3d481f3cd6b47f86783c7ec4c63",
            '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Pay_json_rsp_subtree_include_stats_no_scoped': "b05ed9fa4f7f2f6e52e78976da725716",
            # Api.get_tenant_stats
            '_api_mo_uni_tn_DataDog_json_rsp_subtree_include_stats_no_scoped': "c8e9a0dbceac67fb1149684f7fc7772c",
            # Api.get_tenant_events
            '_api_node_mo_uni_tn_DataDog_json_rsp_subtree_include_event_logs_no_scoped_subtree_order_by_eventRecord_created_desc_page_0_page_size_15': "d0260e4832537b43b1acb38bcfa58063",
        }
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
        except KeyError:
            return {"imdata": []}
        mock_path = os.path.join(FIXTURES_DIR, mock_path)
        mock_path += '.txt'

        log.info(os.listdir(FIXTURES_DIR))

        with open(mock_path, 'r') as f:
            return json.loads(f.read())


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
