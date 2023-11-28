# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy
import ipaddress
import logging
import os
import socket
import sys
from collections import defaultdict

import pytest
from six import iteritems

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.utils.common import get_docker_hostname, to_native_string
from datadog_checks.dev.docker import get_container_ip
from datadog_checks.dev.utils import get_active_env
from datadog_checks.snmp import SnmpCheck

log = logging.getLogger(__name__)

HOST = get_docker_hostname()
PORT = 1161
HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_DIR = os.path.join(HERE, 'compose')
SNMP_LISTENER_ENV = os.environ['SNMP_LISTENER_ENV']
ACTIVE_ENV_NAME = get_active_env()

AUTH_PROTOCOLS = {'MD5': 'usmHMACMD5AuthProtocol', 'SHA': 'usmHMACSHAAuthProtocol'}
PRIV_PROTOCOLS = {'DES': 'usmDESPrivProtocol', 'AES': 'usmAesCfb128Protocol'}
AUTH_KEY = 'doggiepass'
PRIV_KEY = 'doggiePRIVkey'
SNMP_CONTAINER_NAME = 'dd-snmp'

CHECK_TAGS = ['snmp_device:{}'.format(HOST)]

SNMP_CONF = {'ip_address': HOST, 'port': PORT, 'community_string': 'public'}

SNMP_V3_CONF = {
    'name': 'snmp_v3_conf',
    'ip_address': HOST,
    'port': PORT,
    'user': None,
    'authKey': None,
    'privKey': None,
    'authProtocol': None,
    'privProtocol': None,
    'context_name': 'public',
}

MIBS_FOLDER = {'mibs_folder': os.path.join(HERE, "mibs")}

IGNORE_NONINCREASING_OID = {'ignore_nonincreasing_oid': True}

SUPPORTED_METRIC_TYPES = [
    {'OID': "1.3.6.1.2.1.7.1.0", 'name': "IAmACounter32"},  # Counter32
    {'OID': "1.3.6.1.2.1.4.31.1.1.6.1", 'name': "IAmACounter64"},  # Counter64
    {'OID': "1.3.6.1.2.1.4.24.6.0", 'name': "IAmAGauge32"},  # Gauge32
    {'OID': "1.3.6.1.2.1.88.1.1.1.0", 'name': "IAmAnInteger"},  # Integer
]

UNSUPPORTED_METRICS = [{'OID': "1.3.6.1.2.1.25.6.3.1.5.1", 'name': "IAmString"}]  # String (not supported)

CAST_METRICS = [
    {'OID': "1.3.6.1.4.1.2021.10.1.3.1", 'name': "cpuload1"},  # OctetString
    {'OID': "1.3.6.1.4.1.2021.10.1.6.1", 'name': "cpuload2"},  # Opaque
]

CONSTRAINED_OID = [{"MIB": "TCP-MIB", "symbol": "tcpRtoAlgorithm"}]

DUMMY_MIB_OID = [
    ({"MIB": "DUMMY-MIB", "symbol": "scalar"}, AggregatorStub.GAUGE, 10),  # Integer
    # Additional types we support but that are not part of the original SNMP protocol.
    ({"MIB": "DUMMY-MIB", "symbol": "dummyCounterGauge"}, AggregatorStub.GAUGE, 90),  # CounterBasedGauge64
    ({"MIB": "DUMMY-MIB", "symbol": "dummyZeroCounter"}, AggregatorStub.RATE, 120),  # ZeroBasedCounter64
]

FORCED_METRICS = [
    {'OID': "1.3.6.1.2.1.4.24.6.0", 'name': "IAmAGauge32", 'forced_type': 'counter'},  # Gauge32
    {'OID': "1.3.6.1.2.1.4.31.1.1.6.1", 'name': "IAmACounter64", 'forced_type': 'gauge'},  # Counter32
    {'OID': "1.3.6.1.4.1.123456789.1.0", 'name': "IAmAOctetStringFloat", 'forced_type': 'gauge'},  # OctetString float
]
INVALID_FORCED_METRICS = [
    {'OID': "1.3.6.1.2.1.4.24.6.0", 'name': "IAmAGauge32", 'forced_type': 'counter'},  # Gauge32
    {'OID': "1.3.6.1.2.1.4.31.1.1.6.1", 'name': "IAmACounter64", 'forced_type': 'histogram'},  # Counter32
]

SCALAR_OBJECTS = [
    {'OID': "1.3.6.1.2.1.7.1.0", 'name': "udpDatagrams"},
    {'OID': "1.3.6.1.2.1.6.10.0", 'name': "tcpInSegs"},
    {'OID': ".1.3.6.1.6.3.10.2.1.3.0", 'name': "snmpEngineTime"},  # OID with leading dot
    {'MIB': "TCP-MIB", 'symbol': "tcpCurrEstab"},
]

SCALAR_OBJECTS_WITH_TAGS = [
    {'OID': "1.3.6.1.2.1.7.1.0", 'name': "udpDatagrams", 'metric_tags': ['udpdgrams', 'UDP']},
    {'OID': "1.3.6.1.2.1.6.10.0", 'name': "tcpInSegs", 'metric_tags': ['tcpinsegs', 'TCP']},
    {'MIB': "TCP-MIB", 'symbol': "tcpCurrEstab", 'metric_tags': ['MIB', 'TCP', 'estab']},
]

TABULAR_OBJECTS = [
    {
        'MIB': "IF-MIB",
        'table': "ifTable",
        'symbols': ["ifInOctets", "ifOutOctets"],
        'metric_tags': [{'tag': "interface", 'column': "ifDescr"}, {'tag': "dumbindex", 'index': 1}],
    }
]

BULK_TABULAR_OBJECTS = [
    {
        'MIB': "IF-MIB",
        'table': "ifTable",
        'symbols': [
            "ifInOctets",
            "ifOutOctets",
            "ifInUcastPkts",
            "ifInUcastPkts",
            "ifInNUcastPkts",
            "ifInDiscards",
            "ifInErrors",
            "ifInUnknownProtos",
        ],
        'metric_tags': [{'tag': "interface", 'column': "ifDescr"}, {'tag': "dumbindex", 'index': 1}],
    },
    {
        'MIB': "IP-MIB",
        'table': "ipSystemStatsTable",
        'symbols': [
            "ipSystemStatsInReceives",
            "ipSystemStatsHCInReceives",
            "ipSystemStatsInOctets",
            "ipSystemStatsHCInOctets",
            "ipSystemStatsInHdrErrors",
            "ipSystemStatsInNoRoutes",
            "ipSystemStatsInAddrErrors",
            "ipSystemStatsInUnknownProtos",
            "ipSystemStatsInTruncatedPkts",
            "ipSystemStatsInForwDatagrams",
            "ipSystemStatsHCInForwDatagrams",
            "ipSystemStatsReasmReqds",
            "ipSystemStatsReasmOKs",
            "ipSystemStatsReasmFails",
            "ipSystemStatsInDiscards",
            "ipSystemStatsInDelivers",
            "ipSystemStatsHCInDelivers",
            "ipSystemStatsOutRequests",
            "ipSystemStatsHCOutRequests",
            "ipSystemStatsOutNoRoutes",
            "ipSystemStatsOutForwDatagrams",
            "ipSystemStatsHCOutForwDatagrams",
            "ipSystemStatsOutDiscards",
            "ipSystemStatsOutFragReqds",
            "ipSystemStatsOutFragOKs",
            "ipSystemStatsOutFragFails",
            "ipSystemStatsOutFragCreates",
            "ipSystemStatsOutTransmits",
            "ipSystemStatsHCOutTransmits",
            "ipSystemStatsOutOctets",
            "ipSystemStatsHCOutOctets",
            "ipSystemStatsInMcastPkts",
        ],
        'metric_tags': [{'tag': "dumbindex", 'index': 1}],
    },
]

INVALID_METRICS = [
    {
        'MIB': "IF-MIB",
        'table': "noIdeaWhatIAmDoingHere",
        'symbols': ["ImWrong", "MeToo"],
        'metric_tags': [{'tag': "dumbindex", 'index': 1}],
    }
]

PLAY_WITH_GET_NEXT_METRICS = [
    {"OID": "1.3.6.1.2.1.4.31.3.1.3.2", "name": "needFallback"},
    {"OID": "1.3.6.1.2.1.4.31.3.1.3.2.1", "name": "noFallbackAndSameResult"},
]

RESOLVED_TABULAR_OBJECTS = [
    {
        "MIB": "IF-MIB",
        "table": "ifTable",
        "symbols": [
            {"name": "ifInOctets", "OID": "1.3.6.1.2.1.2.2.1.10"},
            {"name": "ifOutOctets", "OID": "1.3.6.1.2.1.2.2.1.16"},
        ],
        "metric_tags": [
            {"tag": "interface", "column": {"name": "ifDescr", "OID": "1.3.6.1.2.1.2.2.1.2"}},
            {"tag": "dumbindex", "index": 1, "mapping": {1: "one", 2: "two", 3: "three", 90: "other"}},
        ],
    }
]

EXCLUDED_E2E_TAG_KEYS = ['agent_version']

snmp_listener_only = pytest.mark.skipif(SNMP_LISTENER_ENV != 'true', reason='Agent snmp lister tests only')
snmp_integration_only = pytest.mark.skipif(SNMP_LISTENER_ENV != 'false', reason='Normal tests')
py3_plus_only = pytest.mark.skipif(sys.version_info[0] < 3, reason='Run test with Python 3+ only')


def generate_instance_config(metrics, template=None):
    template = template if template else SNMP_CONF
    instance_config = copy.copy(template)
    if metrics:
        instance_config['metrics'] = metrics
    return instance_config


def generate_container_instance_config(metrics):
    conf = copy.deepcopy(SNMP_CONF)
    conf['ip_address'] = get_container_ip(SNMP_CONTAINER_NAME)
    return {
        'init_config': {},
        'instances': [generate_instance_config(metrics, template=conf)],
    }


def generate_container_profile_config(community_string, profile=None):
    conf = copy.deepcopy(SNMP_CONF)
    conf['ip_address'] = get_container_ip(SNMP_CONTAINER_NAME)

    init_config = {}

    instance = generate_instance_config([], template=conf)
    instance['community_string'] = community_string
    instance['enforce_mib_constraints'] = False
    if profile is not None:
        instance['profile'] = profile
    return {
        'init_config': init_config,
        'instances': [instance],
    }


def generate_container_profile_config_with_ad(profile):
    host = socket.gethostbyname(get_container_ip(SNMP_CONTAINER_NAME))
    network = ipaddress.ip_network(u'{}/29'.format(host), strict=False).with_prefixlen
    conf = {
        # Make sure the check handles bytes
        'network_address': to_native_string(network),
        'port': PORT,
        'community_string': 'apc_ups',
    }

    init_config = {}

    instance = generate_instance_config([], template=conf)
    instance['community_string'] = profile
    instance['enforce_mib_constraints'] = False
    return {
        'init_config': init_config,
        'instances': [instance],
    }


def generate_v3_instance_config(metrics, name=None, user=None, auth=None, auth_key=None, priv=None, priv_key=None):
    instance_config = generate_instance_config(metrics, SNMP_V3_CONF)

    if name:
        instance_config['name'] = name
    if user:
        instance_config['user'] = user
    if auth:
        instance_config['authProtocol'] = auth
    if auth_key:
        instance_config['authKey'] = auth_key
    if priv:
        instance_config['privProtocol'] = priv
    if priv_key:
        instance_config['privKey'] = priv_key

    return instance_config


def create_check(instance):
    return SnmpCheck('snmp', {}, [instance])


def assert_common_metrics(aggregator, tags=None, is_e2e=False, loader=None):
    assert_common_check_run_metrics(aggregator, tags, is_e2e, loader=loader)
    assert_common_device_metrics(aggregator, tags, is_e2e, loader=loader)


def assert_common_check_run_metrics(aggregator, tags=None, is_e2e=False, loader=None):
    if is_e2e and loader == 'core':
        aggregator.assert_metric('snmp.device.reachable', metric_type=aggregator.GAUGE, tags=tags, at_least=1, value=1)
        aggregator.assert_metric(
            'snmp.device.unreachable', metric_type=aggregator.GAUGE, tags=tags, at_least=1, value=0
        )
        aggregator.assert_metric('snmp.interface.status', metric_type=aggregator.GAUGE, tags=tags, at_least=0, value=1)

    monotonic_type = aggregator.MONOTONIC_COUNT
    if is_e2e:
        monotonic_type = aggregator.COUNT
    loader = loader or 'python'
    if tags is not None:
        tags = tags + ['loader:' + loader]
    aggregator.assert_metric('datadog.snmp.check_duration', metric_type=aggregator.GAUGE, tags=tags)
    aggregator.assert_metric('datadog.snmp.check_interval', metric_type=monotonic_type, tags=tags)
    aggregator.assert_metric('datadog.snmp.submitted_metrics', metric_type=aggregator.GAUGE, tags=tags)


def assert_common_device_metrics(
    aggregator, tags=None, is_e2e=False, count=None, devices_monitored_value=None, loader=None
):
    loader = loader or 'python'
    if tags is not None:
        tags = tags + ['loader:' + loader]
    aggregator.assert_metric(
        'snmp.devices_monitored', metric_type=aggregator.GAUGE, tags=tags, count=count, value=devices_monitored_value
    )


def remove_tags(tags, tag_keys_to_remove):
    """
    Remove tags by excluding tags with specific keys.
    """
    new_tags = []
    for tag in tags:
        for tag_key in tag_keys_to_remove:
            if tag.startswith(tag_key + ':'):
                break
        else:
            new_tags.append(tag)
    return new_tags


def dd_agent_check_wrapper(dd_agent_check, *args, **kwargs):
    """
    dd_agent_check_wrapper is a wrapper around dd_agent_check that will return an aggregator.
    The wrapper will modify tags by excluding EXCLUDED_E2E_TAG_KEYS.
    """
    aggregator = dd_agent_check(*args, **kwargs)
    new_agg_metrics = defaultdict(list)
    for metric_name, metric_list in iteritems(aggregator._metrics):
        new_metrics = []
        for metric in metric_list:
            # metric is a Namedtuple, to modify namedtuple fields we need to use `._replace()`
            new_metric = metric._replace(tags=remove_tags(metric.tags, EXCLUDED_E2E_TAG_KEYS))
            new_metrics.append(new_metric)
        new_agg_metrics[metric_name] = new_metrics

    aggregator._metrics = new_agg_metrics
    return aggregator
