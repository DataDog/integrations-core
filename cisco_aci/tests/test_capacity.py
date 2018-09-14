# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import pytest
import logging
import simplejson as json
from requests import Session

from datadog_checks.cisco_aci.api import SessionWrapper, Api
from datadog_checks.cisco_aci.capacity import Capacity
from datadog_checks.cisco_aci import CiscoACICheck
from datadog_checks.utils.containers import hash_mutable

import conftest
from .common import FIXTURE_LIST_FILE_MAP


log = logging.getLogger('test_cisco_aci')


class ApiMock:
    def __init__(self):
        pass

    def get_eqpt_capacity(self, eqpt):
        return [
            {},
            {
                'other': {}
            },
            {
                'attributes': {}
            },
            {
                'attributes': {"other": "other"}
            },
            {
                'attributes': {"other": "other"},
                "children": []
            },
            {
                'attributes': {"dn": "/pod-3/node-4/"},
                "children": []
            },
            {
                'attributes': {
                    "dn": "/pod-1/node-2/"
                }, "children": [
                    {"eqptcapacityL3TotalUsageCap5min": {"attributes": {
                        "v4TotalEpCapCum": "1",
                        "v6TotalEpCapCum": "2"
                    }}},
                    {"eqptcapacityL3TotalUsage5min": {"attributes": {
                        "v4TotalEpCum": "3",
                        "v6TotalEpCum": "4"
                    }}},
                    {"eqptcapacityVlanUsage5min": {"attributes": {
                        "totalCapCum": "5",
                        "totalCum": "6"
                    }}},
                    {"eqptcapacityPolUsage5min": {"attributes": {
                        "polUsageCapCum": "7",
                        "polUsageCum": "8"
                    }}},
                    {"eqptcapacityMcastUsage5min": {"attributes": {
                        "localEpCapCum": "9",
                        "localEpCum": "10"
                    }}},
                    {"other": ""},
                ]
            }
        ]

    def get_capacity_contexts(self, context):
        return [
            {},
            {"other": {}},
            {"ctxClassCnt": {"attributes": {}}},
            {"ctxClassCnt": {"other": {}}},
            {
                "ctxClassCnt": {
                    "attributes": {
                        "other": "other",
                    }
                }
            }, {
                "ctxClassCnt": {
                    "attributes": {
                        "dn": "/pod-3/node-4/",
                    }
                }
            }, {
                "ctxClassCnt": {
                    "attributes": {
                        "count": "666",
                        "dn": "/pod-1/node-2/",
                        "other": "other"
                    }
                }
            }
        ]

    def get_apic_capacity_limits(self):
        return [
            {},
            {"other": {}},
            {"fvcapRule": {}},
            {"fvcapRule": {"other": {}}},
            {"fvcapRule": {"attributes": {}}},
            {"fvcapRule": {"attributes": {"constraint": "100"}}},
            {
                "fvcapRule": {
                    "attributes": {
                        "subj": "subj1",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "subj": "fabricNode",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "constraint": "1",
                        "subj": "vzBrCP",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "constraint": "2.0",
                        "subj": "fvTenant",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "constraint": "3",
                        "subj": "fvCEp",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "constraint": "4",
                        "subj": "plannerAzureDomainTmpl",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "constraint": "5",
                        "subj": "fvCtx",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "constraint": "6",
                        "subj": "plannerAzureDomainTmpl",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "constraint": "7",
                        "subj": "plannerAzureDomain",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "constraint": "8",
                        "subj": "vnsGraphInst",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "constraint": "9",
                        "subj": "fvBD",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "constraint": "10",
                        "subj": "fvAEPg",
                    }
                }
            }, {
                "fvcapRule": {
                    "attributes": {
                        "constraint": "11",
                        "subj": "plannerVmwareDomain",
                    }
                }
            }
        ]

    def get_apic_capacity_metrics(self, capacity_metric, query=None):
        return [
            {},
            {"other": {}},
            {"moCount": {}},
            {"moCount": {"other": {}}},
            {"moCount": {"attributes": {}}},
            {"moCount": {"attributes": {"count": "666"}}}
        ]


def test_get_eqpt_capacity(aggregator):
    check = CiscoACICheck(conftest.CHECK_NAME, {}, {})
    api = ApiMock()
    capacity = Capacity(api, instance={"tags": ["user_tag:1", "utag:2"]}, check_tags=["check_tag:1", "ctag:2"],
                        gauge=check.gauge, log=check.log)
    capacity._get_eqpt_capacity()
    tags = ['fabric_pod_id:1', 'node_id:2', 'check_tag:1', 'ctag:2', 'user_tag:1', 'utag:2']
    hn = 'pod-1-node-2'
    aggregator.assert_metric('cisco_aci.capacity.leaf.policy_cam.utilized', value=8.0, tags=tags, hostname=hn, count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.vlan.limit', value=5.0, tags=tags, hostname=hn, count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.ipv6_endpoint.limit', value=2.0, tags=tags, hostname=hn, count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.policy_cam.limit', value=7.0, tags=tags, hostname=hn, count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.ipv4_endpoint.limit', value=1.0, tags=tags, hostname=hn, count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.ipv6_endpoint.utilized', value=4.0, tags=tags, hostname=hn,
                             count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.vlan.utilized', value=6.0, tags=tags, hostname=hn, count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.multicast.limit',  value=9.0, tags=tags, hostname=hn, count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.multicast.utilized', value=10.0, tags=tags, hostname=hn, count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.ipv4_endpoint.utilized', value=3.0, tags=tags, hostname=hn,
                             count=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


def test_get_contexts(aggregator):
    check = CiscoACICheck(conftest.CHECK_NAME, {}, {})
    api = ApiMock()
    capacity = Capacity(api, instance={"tags": ["user_tag:1", "utag:2"]}, check_tags=["check_tag:1", "ctag:2"],
                        gauge=check.gauge, log=check.log)
    capacity._get_contexts()
    tags = ['check_tag:1', 'ctag:2', 'user_tag:1', 'utag:2']

    aggregator.assert_metric('cisco_aci.capacity.leaf.bridge_domain.utilized', value=666.0,
                             tags=['fabric_pod_id:1', 'node_id:2'] + tags, hostname='pod-1-node-2', count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.vrf.utilized', value=666.0,
                             tags=['fabric_pod_id:1', 'node_id:2'] + tags, hostname='pod-1-node-2')
    aggregator.assert_metric('cisco_aci.capacity.leaf.endpoint_group.limit', value=3500.0,
                             tags=['fabric_pod_id:1', 'node_id:2'] + tags, hostname='pod-1-node-2', count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.bridge_domain.limit', value=3500.0,
                             tags=['fabric_pod_id:1', 'node_id:2'] + tags, hostname='pod-1-node-2', count=1)
    aggregator.assert_metric('cisco_aci.capacity.leaf.endpoint_group.utilized', value=666.0,
                             tags=['fabric_pod_id:1', 'node_id:2'] + tags, hostname='pod-1-node-2')
    aggregator.assert_metric('cisco_aci.capacity.leaf.vrf.limit',  value=800.0,
                             tags=['fabric_pod_id:1', 'node_id:2'] + tags, hostname='pod-1-node-2', count=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


def test_get_apic_capacity_limits(aggregator):
    check = CiscoACICheck(conftest.CHECK_NAME, {}, {})
    api = ApiMock()
    capacity = Capacity(api, instance={"tags": ["user_tag:1", "utag:2"]}, check_tags=["check_tag:1", "ctag:2"],
                        gauge=check.gauge, log=check.log)
    capacity._get_apic_capacity_limits()
    tags = ['check_tag:1', 'ctag:2', 'user_tag:1', 'utag:2']

    aggregator.assert_metric('cisco_aci.capacity.apic.tenant.limit', value=2.0, tags=tags, hostname='', count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.service_graph.limit', value=8.0, tags=tags, hostname='', count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.bridge_domain.limit', value=9.0, tags=tags, hostname='', count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.azure_domain.endpoint_group.limit', value=7.0, tags=tags,
                             hostname='', count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.vmware_domain.endpoint_group.limit', value=11.0, tags=tags,
                             hostname='', count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.fabric_node.limit', value=0.0, tags=tags, hostname='', count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.contract.limit', value=1.0, tags=tags, hostname='', count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.azure_domain.limit', value=4.0, tags=tags, hostname='', count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.azure_domain.limit', value=6.0, tags=tags, hostname='', count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.endpoint_group.limit', value=10.0, tags=tags, hostname='',
                             count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.private_network.limit', value=5.0, tags=tags, hostname='',
                             count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.endpoint.limit', value=3.0, tags=tags, hostname='', count=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


def test_get_apic_capacity_metrics(aggregator):
    check = CiscoACICheck(conftest.CHECK_NAME, {}, {})
    api = ApiMock()
    capacity = Capacity(api, instance={"tags": ["user_tag:1", "utag:2"]}, check_tags=["check_tag:1", "ctag:2"],
                        gauge=check.gauge, log=check.log)
    capacity._get_apic_capacity_metrics()
    tags = ['check_tag:1', 'ctag:2', 'user_tag:1', 'utag:2']

    aggregator.assert_metric('cisco_aci.capacity.apic.endpoint.utilized', value=666.0, tags=tags, hostname='', count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.bridge_domain.utilized', value=666.0, tags=tags, hostname='',
                             count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.tenant.utilized', value=666.0, tags=tags, hostname='', count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.private_network.utilized', value=666.0, tags=tags, hostname='',
                             count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.endpoint_group.utilized', value=666.0, tags=tags, hostname='',
                             count=1)
    aggregator.assert_metric('cisco_aci.capacity.apic.fabric_node.utilized', value=6.0, tags=tags, hostname='', count=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


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

            mock_path = os.path.join(conftest.CAPACITY_FIXTURES_DIR, mock_path)
            mock_path += '.txt'

            log.info(os.listdir(conftest.CAPACITY_FIXTURES_DIR))

            with open(mock_path, 'r') as f:
                return json.loads(f.read())
        except Exception:
            return {"imdata": []}


@pytest.fixture
def session_mock():
    session = Session()
    setattr(session, 'send', conftest.mock_send)
    fake_session_wrapper = FakeSess(conftest.ACI_URL, session, 'cookie')
    return fake_session_wrapper


def test_capacity_end_to_end(aggregator, session_mock):
    check = CiscoACICheck(conftest.CHECK_NAME, {}, {})
    api = Api(conftest.ACI_URLS, conftest.USERNAME,
              password=conftest.PASSWORD, log=check.log, sessions=[session_mock])
    api._refresh_sessions = False
    check._api_cache[hash_mutable(conftest.CONFIG_WITH_TAGS)] = api

    check.check(conftest.CONFIG_WITH_TAGS)

    tags = ['cisco', 'project:cisco_aci']
    aggregator.assert_metric('cisco_aci.capacity.leaf.bridge_domain.utilized', value=44.0,
                             tags=['fabric_pod_id:1', 'node_id:101'] + tags, hostname='pod-1-node-101')
    aggregator.assert_metric('cisco_aci.capacity.leaf.bridge_domain.utilized', value=1.0,
                             tags=['fabric_pod_id:1', 'node_id:201'] + tags, hostname='pod-1-node-201')
    aggregator.assert_metric('cisco_aci.capacity.leaf.bridge_domain.utilized', value=1.0,
                             tags=['fabric_pod_id:1', 'node_id:202'] + tags, hostname='pod-1-node-202')
    aggregator.assert_metric('cisco_aci.capacity.leaf.bridge_domain.utilized', value=34.0,
                             tags=['fabric_pod_id:1', 'node_id:102'] + tags, hostname='pod-1-node-102')
    aggregator.assert_metric('cisco_aci.capacity.apic.endpoint_group.utilized', value=205.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.private_network.utilized', value=85.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.leaf.bridge_domain.limit', value=3500.0,
                             tags=['fabric_pod_id:1', 'node_id:101'] + tags, hostname='pod-1-node-101')
    aggregator.assert_metric('cisco_aci.capacity.leaf.bridge_domain.limit', value=3500.0,
                             tags=['fabric_pod_id:1', 'node_id:201'] + tags, hostname='pod-1-node-201')
    aggregator.assert_metric('cisco_aci.capacity.leaf.bridge_domain.limit', value=3500.0,
                             tags=['fabric_pod_id:1', 'node_id:202'] + tags, hostname='pod-1-node-202')
    aggregator.assert_metric('cisco_aci.capacity.leaf.bridge_domain.limit', value=3500.0,
                             tags=['fabric_pod_id:1', 'node_id:102'] + tags, hostname='pod-1-node-102')
    aggregator.assert_metric('cisco_aci.capacity.apic.tenant.utilized', value=90.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.leaf.endpoint_group.utilized', value=94.0,
                             tags=['fabric_pod_id:1', 'node_id:101'] + tags, hostname='pod-1-node-101')
    aggregator.assert_metric('cisco_aci.capacity.leaf.endpoint_group.utilized', value=0.0,
                             tags=['fabric_pod_id:1', 'node_id:201'] + tags, hostname='pod-1-node-201')
    aggregator.assert_metric('cisco_aci.capacity.leaf.endpoint_group.utilized', value=0.0,
                             tags=['fabric_pod_id:1', 'node_id:202'] + tags, hostname='pod-1-node-202')
    aggregator.assert_metric('cisco_aci.capacity.leaf.endpoint_group.utilized', value=78.0,
                             tags=['fabric_pod_id:1', 'node_id:102'] + tags, hostname='pod-1-node-102')
    aggregator.assert_metric('cisco_aci.capacity.apic.endpoint_group.limit', value=15000.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.leaf.endpoint_group.limit', value=3500.0,
                             tags=['fabric_pod_id:1', 'node_id:101'] + tags, hostname='pod-1-node-101')
    aggregator.assert_metric('cisco_aci.capacity.leaf.endpoint_group.limit', value=3500.0,
                             tags=['fabric_pod_id:1', 'node_id:201'] + tags, hostname='pod-1-node-201')
    aggregator.assert_metric('cisco_aci.capacity.leaf.endpoint_group.limit', value=3500.0,
                             tags=['fabric_pod_id:1', 'node_id:202'] + tags, hostname='pod-1-node-202')
    aggregator.assert_metric('cisco_aci.capacity.leaf.endpoint_group.limit', value=3500.0,
                             tags=['fabric_pod_id:1', 'node_id:102'] + tags, hostname='pod-1-node-102')
    aggregator.assert_metric('cisco_aci.capacity.apic.endpoint.limit', value=180000.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.endpoint.utilized', value=76.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.bridge_domain.utilized', value=154.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.vmware_domain.limit', value=5.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.private_network.limit', value=3000.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.leaf.vrf.utilized', value=32.0,
                             tags=['fabric_pod_id:1', 'node_id:101'] + tags, hostname='pod-1-node-101')
    aggregator.assert_metric('cisco_aci.capacity.leaf.vrf.utilized', value=4.0,
                             tags=['fabric_pod_id:1', 'node_id:201'] + tags, hostname='pod-1-node-201')
    aggregator.assert_metric('cisco_aci.capacity.leaf.vrf.utilized', value=4.0,
                             tags=['fabric_pod_id:1', 'node_id:202'] + tags, hostname='pod-1-node-202')
    aggregator.assert_metric('cisco_aci.capacity.leaf.vrf.utilized', value=27.0,
                             tags=['fabric_pod_id:1', 'node_id:102'] + tags, hostname='pod-1-node-102')
    aggregator.assert_metric('cisco_aci.capacity.apic.contract.limit', value=1000.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.azure_domain.endpoint_group.limit', value=9000.0,
                             tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.fabric_node.limit', value=200.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.bridge_domain.limit', value=15000.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.fabric_node.utilized', value=2.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.tenant.limit', value=3000.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.leaf.vrf.limit', value=800.0,
                             tags=['fabric_pod_id:1', 'node_id:101'] + tags,  hostname='pod-1-node-101')
    aggregator.assert_metric('cisco_aci.capacity.leaf.vrf.limit', value=800.0,
                             tags=['fabric_pod_id:1', 'node_id:201'] + tags, hostname='pod-1-node-201')
    aggregator.assert_metric('cisco_aci.capacity.leaf.vrf.limit', value=800.0,
                             tags=['fabric_pod_id:1', 'node_id:202'] + tags, hostname='pod-1-node-202')
    aggregator.assert_metric('cisco_aci.capacity.leaf.vrf.limit', value=800.0,
                             tags=['fabric_pod_id:1', 'node_id:102'] + tags, hostname='pod-1-node-102')
    aggregator.assert_metric('cisco_aci.capacity.apic.vmware_domain.endpoint_group.limit', value=15000.0,
                             tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.azure_domain.limit', value=5.0, tags=tags, hostname='')
    aggregator.assert_metric('cisco_aci.capacity.apic.service_graph.limit', value=600.0, tags=tags, hostname='')
