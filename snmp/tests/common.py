# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy
import logging
import os

from datadog_checks.utils.common import get_docker_hostname

log = logging.getLogger(__name__)

HOST = get_docker_hostname()
PORT = 1161
HERE = os.path.dirname(os.path.abspath(__file__))

AUTH_PROTOCOLS = {'MD5': 'usmHMACMD5AuthProtocol', 'SHA': 'usmHMACSHAAuthProtocol'}
PRIV_PROTOCOLS = {'DES': 'usmDESPrivProtocol', 'AES': 'usmAesCfb128Protocol'}
AUTH_KEY = 'doggiepass'
PRIV_KEY = 'doggiePRIVkey'

CHECK_TAGS = ['snmp_device:{}'.format(HOST)]


SNMP_CONF = {
    'name': 'snmp_conf',
    'ip_address': HOST,
    'port': PORT,
    'community_string': 'public',
}

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

MIBS_FOLDER = {
    'mibs_folder': os.path.join(HERE, "mibs")
}

IGNORE_NONINCREASING_OID = {
    'ignore_nonincreasing_oid': True
}

SUPPORTED_METRIC_TYPES = [
    {
        'OID': "1.3.6.1.2.1.7.1.0",             # Counter32
        'name': "IAmACounter32"
    }, {
        'OID': "1.3.6.1.2.1.4.31.1.1.6.1",      # Counter64
        'name': "IAmACounter64"
    }, {
        'OID': "1.3.6.1.2.1.4.24.6.0",          # Gauge32
        'name': "IAmAGauge32"
    }, {
        'OID': "1.3.6.1.2.1.88.1.1.1.0",        # Integer
        'name': "IAmAnInteger"
    }
]

UNSUPPORTED_METRICS = [
    {
        'OID': "1.3.6.1.2.1.25.6.3.1.5.1",    # String (not supported)
        'name': "IAmString"
    }
]

CONSTRAINED_OID = [
    {
        "MIB": "RFC1213-MIB",
        "symbol": "tcpRtoAlgorithm",
    }
]

DUMMY_MIB_OID = [
    {
        "MIB": "DUMMY-MIB",
        "symbol": "scalar",
    }
]

FORCED_METRICS = [
    {
        'OID': "1.3.6.1.2.1.4.24.6.0",          # Gauge32
        'name': "IAmAGauge32",
        'forced_type': 'counter'

    }, {
        'OID': "1.3.6.1.2.1.4.31.1.1.6.1",      # Counter32
        'name': "IAmACounter64",
        'forced_type': 'gauge'
    }
]
INVALID_FORCED_METRICS = [
    {
        'OID': "1.3.6.1.2.1.4.24.6.0",          # Gauge32
        'name': "IAmAGauge32",
        'forced_type': 'counter'

    }, {
        'OID': "1.3.6.1.2.1.4.31.1.1.6.1",      # Counter32
        'name': "IAmACounter64",
        'forced_type': 'histogram'
    }
]

SCALAR_OBJECTS = [
    {
        'OID': "1.3.6.1.2.1.7.1.0",
        'name': "udpDatagrams"
    }, {
        'OID': "1.3.6.1.2.1.6.10.0",
        'name': "tcpInSegs"
    }, {
        'MIB': "TCP-MIB",
        'symbol': "tcpCurrEstab",
    }
]

SCALAR_OBJECTS_WITH_TAGS = [
    {
        'OID': "1.3.6.1.2.1.7.1.0",
        'name': "udpDatagrams",
        'metric_tags': ['udpdgrams', 'UDP']
    }, {
        'OID': "1.3.6.1.2.1.6.10.0",
        'name': "tcpInSegs",
        'metric_tags': ['tcpinsegs', 'TCP']
    }, {
        'MIB': "TCP-MIB",
        'symbol': "tcpCurrEstab",
        'metric_tags': ['MIB', 'TCP', 'estab']
    }
]

TABULAR_OBJECTS = [{
    'MIB': "IF-MIB",
    'table': "ifTable",
    'symbols': ["ifInOctets", "ifOutOctets"],
    'metric_tags': [
        {
            'tag': "interface",
            'column': "ifDescr"
        }, {
            'tag': "dumbindex",
            'index': 1
        }
    ]
}]

INVALID_METRICS = [
    {
        'MIB': "IF-MIB",
        'table': "noIdeaWhatIAmDoingHere",
        'symbols': ["ifInOctets", "ifOutOctets"],
    }
]

PLAY_WITH_GET_NEXT_METRICS = [
    {
        "OID": "1.3.6.1.2.1.4.31.3.1.3.2",
        "name": "needFallback"
    }, {
        "OID": "1.3.6.1.2.1.4.31.3.1.3.2.1",
        "name": "noFallbackAndSameResult"
    }
]


def generate_instance_config(metrics, template=None):
    template = template if template else SNMP_CONF
    instance_config = copy.copy(template)
    instance_config['metrics'] = metrics
    instance_config['name'] = HOST
    return instance_config


def generate_v3_instance_config(metrics, name=None, user=None,
                                auth=None, auth_key=None, priv=None, priv_key=None):
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
