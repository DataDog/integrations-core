# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License see LICENSE

import hashlib
import json
import logging
import os

from datadog_checks.cisco_aci.api import SessionWrapper

log = logging.getLogger('test_cisco_aci')

CHECK_NAME = 'cisco_aci'

CERTIFICATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certificate')
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
CAPACITY_FIXTURES_DIR = os.path.join(FIXTURES_DIR, 'capacity')
FABRIC_FIXTURES_DIR = os.path.join(FIXTURES_DIR, 'fabric')
TENANT_FIXTURES_DIR = os.path.join(FIXTURES_DIR, 'tenant')
ALL_FIXTURE_DIR = [FIXTURES_DIR, CAPACITY_FIXTURES_DIR, FABRIC_FIXTURES_DIR, TENANT_FIXTURES_DIR]

USERNAME = 'datadog'
PASSWORD = 'datadog'
ACI_URL = 'https://datadoghq.com'
ACI_URLS = [ACI_URL]
CONFIG = {'aci_urls': ACI_URLS, 'username': USERNAME, 'pwd': PASSWORD, 'tenant': ['DataDog']}

CONFIG_WITH_TAGS = {
    'aci_urls': ACI_URLS,
    'username': USERNAME,
    'pwd': PASSWORD,
    'tenant': ['DataDog'],
    "tags": ["project:cisco_aci"],
    "send_ndm_metadata": True,
}

# list of fixture names
FIXTURE_LIST = [
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_json_query_target_subtree_target_subtree_class_fvAEPg',
    # d98210e57060ed7285a4fa7434c53ff1 - Api.get_epgs
    '_api_mo_uni_tn_DataDog_ap_DtDg_test_AP_json_query_target_subtree_target_subtree_class_fvAEPg',
    # 4b07d389b109401afcc2c42bdca0f2b2 - Api.get_epgs
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_json_query_target_subtree_target_subtree_class_fvAEPg',
    # 43410607b378cfa340146247a8b422b9 - Api.get_epgs
    '_api_mo_topology_pod_1_node_201_sys_json_rsp_subtree_include_stats_no_scoped_page_size_20',
    # bd2db6fd496f3b1ee12ac533e3224c21 - Api.get_node_stats
    '_api_mo_topology_pod_1_node_102_sys_json_rsp_subtree_include_stats_no_scoped_page_size_20',
    # 38eea560b59819b60a356010e9b3c191 - Api.get_node_stats
    '_api_mo_topology_pod_1_node_202_sys_json_rsp_subtree_include_stats_no_scoped_page_size_20',
    # 7660dffc9226f865526ffe82fe4694fa - Api.get_node_stats
    '_api_mo_topology_pod_1_node_101_sys_json_rsp_subtree_include_stats_no_scoped_page_size_20',
    # d121d04c8171c3095561ca593dc2de5d - Api.get_node_stats
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jeti1_json_rsp_subtree_include_stats_no_scoped',
    # f44f8e9a9afe5d47c8b27d06b6458200 - Api.get_epg_stats
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jeti2_json_rsp_subtree_include_stats_no_scoped',
    # d4efb7c9b80929991dd91850d9ddceef - Api.get_epg_stats
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_MiscAppVMs_json_rsp_subtree_include_stats_no_scoped',
    # 288a353bc9fed8f571d78076cb1585ae - Api.get_epg_stats
    '_api_mo_uni_tn_DataDog_ap_DtDg_test_AP_epg_Test_EPG_json_rsp_subtree_include_stats_no_scoped',
    # 3f8f3374048d7b5b3a38566765f35cc2 - Api.get_epg_stats
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Inv_json_rsp_subtree_include_stats_no_scoped',
    # eb4804e1e68e00353c89b13b56b9d7b9 - Api.get_epg_stats
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Ord_json_rsp_subtree_include_stats_no_scoped',
    # af6ca37b21581b58b9901e23dd02cae9 - Api.get_epg_stats
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Ecomm_json_rsp_subtree_include_stats_no_scoped',
    # f929ec691d62a0d70a12e51fc18b4321 - Api.get_epg_stats
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jetty_Controller_json_rsp_subtree_include_stats_no_scoped',
    # 7034a3d481f3cd6b47f86783c7ec4c63 - Api.get_epg_stats
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Pay_json_rsp_subtree_include_stats_no_scoped',
    # b05ed9fa4f7f2f6e52e78976da725716 - Api.get_epg_stats
    '_api_class_fvBD_json_rsp_subtree_include_count',
    # 2b77c071f172dc404574adca6de263d1 - Api.get_apic_capacity_metrics
    '_api_class_fvTenant_json_rsp_subtree_include_count',
    # 3d8273b2eccc0e7b8ddf73c0bcc0dbc9 - Api.get_apic_capacity_metrics
    '_api_class_fvCEp_json_rsp_subtree_include_count',
    # 955e116c3ee8a1101c00ce000baf05f0 - Api.get_apic_capacity_metrics
    '_api_class_fvAEPg_json_rsp_subtree_include_count',
    # 1ee00ee7448fe5900c1a18d70741a6ab - Api.get_apic_capacity_metrics
    '_api_class_fabricNode_json_query_target_filter_eq_fabricNode_role__leaf__',
    # c0526b62f52c9e8956990035baa96382 - Api.get_apic_capacity_metrics
    '_api_class_fvCtx_json_rsp_subtree_include_count',
    # d8ea046fd4b1831561393f0b0e7055ab - Api.get_apic_capacity_metrics
    '_api_mo_uni_fabric_compcat_default_fvsw_default_capabilities_json_query_target_children_target_subtree_class_fvcapRule',  # noqa: E501
    # d9a173b8bee4de1024bdf1671cb09aa2 - Api.get_apic_capacity_limits
    '_api_node_class_ctxClassCnt_json_rsp_subtree_class_l2BD',
    # 16c2a93c855b8b0039fa41f7d1fd87c7 - Api.get_capacity_contexts
    '_api_node_class_ctxClassCnt_json_rsp_subtree_class_l3Dom',
    # caf41b4bc51dc6f145c5379828a9762e - Api.get_capacity_contexts
    '_api_node_class_ctxClassCnt_json_rsp_subtree_class_fvEpP',
    # 3a3b3fccaf27c95600f33e9c238916d6 - Api.get_capacity_contexts
    '_api_node_mo_topology_pod_1_node_1_sys_proc_json_rsp_subtree_include_stats_no_scoped_rsp_subtree_class_procMemHist5min_procCPUHist5min',  # noqa: E501
    # da3cc25775b42c6e85bf8e389cde346c - Api.get_controller_proc_metrics
    '_api_node_mo_topology_pod_1_node_2_sys_proc_json_rsp_subtree_include_stats_no_scoped_rsp_subtree_class_procMemHist5min_procCPUHist5min',  # noqa: E501
    # 363740b68eff24d19f99f62266029e66 - Api.get_controller_proc_metrics
    '_api_node_mo_topology_pod_1_node_3_sys_proc_json_rsp_subtree_include_stats_no_scoped_rsp_subtree_class_procMemHist5min_procCPUHist5min',  # noqa: E501
    # ee5cd35d0ce16d8d0b7c8057d9d53f37 - Api.get_controller_proc_metrics
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jetty_Controller_json_query_target_subtree_target_subtree_class_fvCEp',  # noqa: E501
    # 28431f4c95e37bbfce84c0d5b82c08e6 - Api.get_epg_meta
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_MiscAppVMs_json_query_target_subtree_target_subtree_class_fvCEp',  # noqa: E501
    # f81112b93297d7112561cde49cd0c927 - Api.get_epg_meta
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Inv_json_query_target_subtree_target_subtree_class_fvCEp',
    # e5192f427b93b4c3948b53eb060db652 - Api.get_epg_meta
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Ecomm_json_query_target_subtree_target_subtree_class_fvCEp',  # noqa: E501
    # e3ab944329625480809e8350724d6f7a - Api.get_epg_meta
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jeti1_json_query_target_subtree_target_subtree_class_fvCEp',
    # 6ea50eec45df7090c11060ae0642fdf1 - Api.get_epg_meta
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jeti2_json_query_target_subtree_target_subtree_class_fvCEp',
    # 4507ab28dfda9c6ad0c6adc79465856d - Api.get_epg_meta
    '_api_mo_uni_tn_DataDog_ap_DtDg_test_AP_epg_Test_EPG_json_query_target_subtree_target_subtree_class_fvCEp',
    # 2a60e74b54870113b67e6ed7f8994d53 - Api.get_epg_meta
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Pay_json_query_target_subtree_target_subtree_class_fvCEp',
    # 603cc1278c410b07905c2c35b49afbe6 - Api.get_epg_meta
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Ord_json_query_target_subtree_target_subtree_class_fvCEp',
    # b9ec4494d631d05122fd7fb4baf0877d - Api.get_epg_meta
    '_api_node_class_topology_pod_1_node_102_l1PhysIf_json_rsp_subtree_children_rsp_subtree_class_ethpmPhysIf',
    # 79af98fe9c1069b329af3b4828712ddd - Api.get_eth_list -> 9d167692ace22bc1013437072c55a641
    '_api_node_class_topology_pod_1_node_201_l1PhysIf_json_rsp_subtree_children_rsp_subtree_class_ethpmPhysIf',
    # ded65ac48170a7a3d8914950607e4e18 - Api.get_eth_list -> 2569ee885cad13ed336e5b4c8bd6dab4
    '_api_node_class_topology_pod_1_node_101_l1PhysIf_json_rsp_subtree_children_rsp_subtree_class_ethpmPhysIf',
    # dace1ecad6f3d9a50eb8d4a15631ba88 - Api.get_eth_list -> 62cb899b6e7f6b81035914cfac47b915
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jeti1_json_query_target_subtree_target_subtree_class_fvRsCEpToPathEp',  # noqa: E501
    # e2b226f554c9f77aafd9b66b4cf59383 - Api.get_eth_list_for_epg
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Ecomm_json_query_target_subtree_target_subtree_class_fvRsCEpToPathEp',  # noqa: E501
    # bac89bea75dbf42e5108b31ee5f2e4c6 - Api.get_eth_list_for_epg
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Ord_json_query_target_subtree_target_subtree_class_fvRsCEpToPathEp',  # noqa: E501
    # e1d65d50c73beddb317b0ca66f97ce4b - Api.get_eth_list_for_epg
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jetty_Controller_json_query_target_subtree_target_subtree_class_fvRsCEpToPathEp',  # noqa: E501
    # 55444ab1c3112431390bb132ef8ea799 - Api.get_eth_list_for_epg
    '_api_mo_uni_tn_DataDog_ap_DtDg_test_AP_epg_Test_EPG_json_query_target_subtree_target_subtree_class_fvRsCEpToPathEp',  # noqa: E501
    # 7704343d94932b9020928c6b75edde7a - Api.get_eth_list_for_epg
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_epg_DtDg_Jeti2_json_query_target_subtree_target_subtree_class_fvRsCEpToPathEp',  # noqa: E501
    # c6b444a3748e83d5d5173802e2cc8766 - Api.get_eth_list_for_epg
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Inv_json_query_target_subtree_target_subtree_class_fvRsCEpToPathEp',  # noqa: E501
    # 761de56d98771ada5db2c5d402347831 - Api.get_eth_list_for_epg
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_MiscAppVMs_json_query_target_subtree_target_subtree_class_fvRsCEpToPathEp',  # noqa: E501
    # 192e2d8a58b2117282557295dc503b0a - Api.get_eth_list_for_epg
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_epg_DtDg_Pay_json_query_target_subtree_target_subtree_class_fvRsCEpToPathEp',  # noqa: E501
    # e001f001b7ac8da3335f8ef8bad17129 - Api.get_eth_list_for_epg
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP1_EcommerceApp_json_rsp_subtree_include_stats_no_scoped',
    # 363e27e35a42bb987c121709284b529f - Api.get_app_stats
    '_api_mo_uni_tn_DataDog_ap_DtDg_test_AP_json_rsp_subtree_include_stats_no_scoped',
    # 1c7d7ebf0b75333689662feb19f63ede - Api.get_app_stats
    '_api_mo_uni_tn_DataDog_ap_DtDg_AP2_Jeti_json_rsp_subtree_include_stats_no_scoped',
    # 10b987e92abaab8d843e6bee5ab6aef0 - Api.get_app_stats
    '_api_mo_topology_json_query_target_subtree_target_subtree_class_fabricNode',
    # 2e82232a722241e59f27ac3742934e7e - Api.get_fabric_nodes
    '_api_node_mo_topology_pod_1_node_102_sys_procsys_json_rsp_subtree_include_stats_no_scoped_rsp_subtree_class_procSysMemHist5min_procSysCPUHist5min',  # noqa: E501
    # 39d31c3f91411cd6018abd79e222d0cf - Api.get_spine_proc_metrics
    '_api_node_mo_topology_pod_1_node_202_sys_procsys_json_rsp_subtree_include_stats_no_scoped_rsp_subtree_class_procSysMemHist5min_procSysCPUHist5min',  # noqa: E501
    # 37ed36e29dc28fecf6ebc21cd2714477 - Api.get_spine_proc_metrics
    '_api_node_mo_topology_pod_1_node_201_sys_procsys_json_rsp_subtree_include_stats_no_scoped_rsp_subtree_class_procSysMemHist5min_procSysCPUHist5min',  # noqa: E501
    # b0c46630b68d344089f7209c814e216e - Api.get_spine_proc_metrics
    '_api_node_mo_topology_pod_1_node_101_sys_procsys_json_rsp_subtree_include_stats_no_scoped_rsp_subtree_class_procSysMemHist5min_procSysCPUHist5min',  # noqa: E501
    # 1df5692a384c4dd76bb6aaeec9e5f922 - Api.get_spine_proc_metrics
    '_api_mo_topology_pod_1_json_rsp_subtree_include_stats_no_scoped_page_size_20',
    # 0d11d458b6d31906696642f74bf016cc - Api.get_pod_stats
    '_api_class_eqptcapacityEntity_json_query_target_self_rsp_subtree_include_stats_rsp_subtree_class_eqptcapacityL3TotalUsage5min',  # noqa: E501
    # cb5f39f666fdef06a4438813d0814611 - Api.get_eqpt_capacity
    '_api_class_eqptcapacityEntity_json_query_target_self_rsp_subtree_include_stats_rsp_subtree_class_eqptcapacityVlanUsage5min',  # noqa: E501
    # 642f9c4d4bffe9e9bad4ad01a34c924e - Api.get_eqpt_capacity
    '_api_class_eqptcapacityEntity_json_query_target_self_rsp_subtree_include_stats_rsp_subtree_class_eqptcapacityPolUsage5min',  # noqa: E501
    # a32256a38e5ae47ec67a4fe42a487df7 - Api.get_eqpt_capacity
    '_api_class_eqptcapacityEntity_json_query_target_self_rsp_subtree_include_stats_rsp_subtree_class_eqptcapacityMcastUsage5min',  # noqa: E501
    # 1e4f33f96dd87955dc6e04b62fdb10f1 - Api.get_eqpt_capacity
    '_api_class_eqptcapacityEntity_json_query_target_self_rsp_subtree_include_stats_rsp_subtree_class_eqptcapacityL3TotalUsageCap5min',  # noqa: E501
    # 0d6ca781810665156211b355129ba2f1 - Api.get_eqpt_capacity
    '_api_mo_topology_json_query_target_subtree_target_subtree_class_fabricPod',
    # 643d217904f09445fbc9f7b43cd131f0 - Api.get_fabric_pods
    '_api_node_mo_uni_tn_DataDog_json_rsp_subtree_include_event_logs_no_scoped_subtree_order_by_eventRecord_created_desc_page_0_page_size_15',  # noqa: E501
    # d0260e4832537b43b1acb38bcfa58063 - Api.get_tenant_events
    '_api_mo_uni_tn_DataDog_json_query_target_subtree_target_subtree_class_fvAp',
    # 4efe80304d50330f5ed0f79252ef0a84 - Api.get_apps
    '_api_mo_uni_tn_DataDog_json_rsp_subtree_include_stats_no_scoped',
    # c8e9a0dbceac67fb1149684f7fc7772c - Api.get_tenant_stats
    '_api_node_class_lldpAdjEp_json',
    # f3713df3a586908a3a11f4c356153519 - Api.get_lldp_adj_eps
    '_api_node_class_cdpAdjEp_json',
    # 588ea77fffc6df4b37dfdfa4290cdc89 - Api.get_cdp_adj_eps
    '_api_node_class_topology_pod_1_node_102_l1PhysIf_json_rsp_subtree_children_rsp_subtree_include_stats_rsp_subtree_class_ethpmPhysIf_eqptEgrTotal5min_eqptIngrTotal5min_eqptEgrDropPkts5min_eqptEgrBytes5min_eqptIngrBytes5min',
    # fde05c4b654d2d8129c772cd5a20cbce - Api.get_eth_list_and_stats
    '_api_node_class_topology_pod_1_node_201_l1PhysIf_json_rsp_subtree_children_rsp_subtree_include_stats_rsp_subtree_class_ethpmPhysIf_eqptEgrTotal5min_eqptIngrTotal5min_eqptEgrDropPkts5min_eqptEgrBytes5min_eqptIngrBytes5min',
    # 9ec9c2e1bcd513274516713bc3f68724 - Api.get_eth_list_and_stats
    '_api_node_class_topology_pod_1_node_101_l1PhysIf_json_rsp_subtree_children_rsp_subtree_include_stats_rsp_subtree_class_ethpmPhysIf_eqptEgrTotal5min_eqptIngrTotal5min_eqptEgrDropPkts5min_eqptEgrBytes5min_eqptIngrBytes5min',
    # 9bd6720132f1eef5ae8ec7d6438d9c6b - Api.get_eth_list_and_stats
]

# The map will contain the md5 hash to the fixture
# name. The file on disk should be named with the
# {MD5 hash}.txt of the mock_path used.
FIXTURE_LIST_FILE_MAP = {}
for fixture in FIXTURE_LIST:
    FIXTURE_LIST_FILE_MAP[fixture] = hashlib.md5(fixture.encode('utf-8')).hexdigest()


class FakeSessionWrapper(SessionWrapper):
    """This mock:
    1. Takes the requested path and replace all special characters to underscore
    2. Fetch the corresponding hash from common.FIXTURE_LIST_FILE_MAP
    3. Returns the corresponding file content
    """

    fixture_dirs = ALL_FIXTURE_DIR

    def login(self, password):
        self.apic_cookie = 'cookie'

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
        mock_path = FIXTURE_LIST_FILE_MAP[mock_path]
        for p in self.fixture_dirs:
            path = os.path.join(p, mock_path)
            path += '.txt'

            try:
                log.info(os.listdir(p))
                with open(path, 'r') as f:
                    return json.loads(f.read())
            except Exception:
                continue
        return {"imdata": []}


class FakeCapacitySessionWrapper(FakeSessionWrapper):
    fixture_dirs = [CAPACITY_FIXTURES_DIR]


class FakeTenantSessionWrapper(FakeSessionWrapper):
    fixture_dirs = [TENANT_FIXTURES_DIR]


class FakeFabricSessionWrapper(FakeSessionWrapper):
    fixture_dirs = [FABRIC_FIXTURES_DIR]
