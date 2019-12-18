# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy
import logging
import os

from datadog_checks.snmp import SnmpCheck
from datadog_checks.utils.common import get_docker_hostname

log = logging.getLogger(__name__)

HOST = get_docker_hostname()
PORT = 1161
HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_DIR = os.path.join(HERE, 'compose')

AUTH_PROTOCOLS = {'MD5': 'usmHMACMD5AuthProtocol', 'SHA': 'usmHMACSHAAuthProtocol'}
PRIV_PROTOCOLS = {'DES': 'usmDESPrivProtocol', 'AES': 'usmAesCfb128Protocol'}
AUTH_KEY = 'doggiepass'
PRIV_KEY = 'doggiePRIVkey'

CHECK_TAGS = ['snmp_device:{}'.format(HOST)]

SNMP_CONF = {'name': 'snmp_conf', 'ip_address': HOST, 'port': PORT, 'community_string': 'public', 'autofetch': True}

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

CONSTRAINED_OID = [{"MIB": "RFC1213-MIB", "symbol": "tcpRtoAlgorithm"}]

DUMMY_MIB_OID = [{"MIB": "DUMMY-MIB", "symbol": "scalar"}]

FORCED_METRICS = [
    {'OID': "1.3.6.1.2.1.4.24.6.0", 'name': "IAmAGauge32", 'forced_type': 'counter'},  # Gauge32
    {'OID': "1.3.6.1.2.1.4.31.1.1.6.1", 'name': "IAmACounter64", 'forced_type': 'gauge'},  # Counter32
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
    },
]

INVALID_METRICS = [{'MIB': "IF-MIB", 'table': "noIdeaWhatIAmDoingHere", 'symbols': ["ImWrong", "MeToo"]}]

PLAY_WITH_GET_NEXT_METRICS = [
    {"OID": "1.3.6.1.2.1.4.31.3.1.3.2", "name": "needFallback"},
    {"OID": "1.3.6.1.2.1.4.31.3.1.3.2.1", "name": "noFallbackAndSameResult"},
]


def generate_instance_config(metrics, template=None):
    template = template if template else SNMP_CONF
    instance_config = copy.copy(template)
    instance_config['metrics'] = metrics
    instance_config['name'] = HOST
    return instance_config


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
