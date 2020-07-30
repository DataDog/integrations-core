# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import ipaddress
import logging
import os
import socket
import time

import mock
import pytest
import yaml

from datadog_checks.base import ConfigurationError, to_native_string
from datadog_checks.dev import temp_dir
from datadog_checks.snmp import SnmpCheck

from . import common

pytestmark = [pytest.mark.usefixtures("dd_environment"), common.python_autodiscovery_only]


def test_command_generator():
    """
    Command generator's parameters should match init_config
    """
    instance = common.generate_instance_config(common.CONSTRAINED_OID)
    check = SnmpCheck('snmp', common.MIBS_FOLDER, [instance])
    config = check._config

    # Test command generator MIB source
    mib_folders = config._snmp_engine.getMibBuilder().getMibSources()
    full_path_mib_folders = [f.fullPath() for f in mib_folders]
    assert check.ignore_nonincreasing_oid is False  # Default value

    check = SnmpCheck('snmp', common.IGNORE_NONINCREASING_OID, [instance])
    assert check.ignore_nonincreasing_oid

    assert common.MIBS_FOLDER["mibs_folder"] in full_path_mib_folders


def test_type_support(aggregator):
    """
    Support expected types
    """
    metrics = common.SUPPORTED_METRIC_TYPES + common.UNSUPPORTED_METRICS
    instance = common.generate_instance_config(metrics)
    check = common.create_check(instance)

    check.check(instance)

    # Test metrics
    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=1)
    for metric in common.UNSUPPORTED_METRICS:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=0)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_transient_error(aggregator):
    instance = common.generate_instance_config(common.SUPPORTED_METRIC_TYPES)
    check = common.create_check(instance)

    with mock.patch('datadog_checks.snmp.commands._handle_error', side_effect=RuntimeError):
        check.check(instance)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.CRITICAL, tags=common.CHECK_TAGS, at_least=1)

    check.check(instance)
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)


def test_snmpget(aggregator):
    """
    When failing with 'snmpget' command, SNMP check falls back to 'snmpgetnext'

        > snmpget -v2c -c public localhost:11111 1.3.6.1.2.1.25.6.3.1.4
        iso.3.6.1.2.1.25.6.3.1.4 = No Such Instance currently exists at this OID
        > snmpgetnext -v2c -c public localhost:11111 1.3.6.1.2.1.25.6.3.1.4
        iso.3.6.1.2.1.25.6.3.1.4.0 = INTEGER: 4
    """
    instance = common.generate_instance_config(common.PLAY_WITH_GET_NEXT_METRICS)
    check = common.create_check(instance)

    check.check(instance)

    # Test metrics
    for metric in common.PLAY_WITH_GET_NEXT_METRICS:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, at_least=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_custom_mib(aggregator):
    instance = common.generate_instance_config([oid for oid, _, _ in common.DUMMY_MIB_OID])
    instance["community_string"] = "dummy"

    check = SnmpCheck('snmp', common.MIBS_FOLDER, [instance])
    check.check(instance)

    # Test metrics
    for metric, metric_type, value in common.DUMMY_MIB_OID:
        metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
        aggregator.assert_metric(metric_name, metric_type=metric_type, count=1, value=value, tags=common.CHECK_TAGS)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)


def test_scalar(aggregator):
    """
    Support SNMP scalar objects
    """
    instance = common.generate_instance_config(common.SCALAR_OBJECTS)
    check = common.create_check(instance)

    check.check(instance)

    # Test metrics
    for metric in common.SCALAR_OBJECTS:
        metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_enforce_constraint(aggregator):
    instance = common.generate_instance_config(common.CONSTRAINED_OID)
    instance["community_string"] = "constraint"
    instance["enforce_mib_constraints"] = True
    check = common.create_check(instance)

    check.check(instance)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.CRITICAL, tags=common.CHECK_TAGS, at_least=1)

    assert "failed at: ValueConstraintError" in aggregator.service_checks("snmp.can_check")[0].message


def test_unenforce_constraint(aggregator):
    """
    Allow ignoring constraints
    """
    instance = common.generate_instance_config(common.CONSTRAINED_OID)
    instance["community_string"] = "constraint"
    instance["enforce_mib_constraints"] = False
    check = common.create_check(instance)
    check.check(instance)

    # Test metrics
    for metric in common.CONSTRAINED_OID:
        metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_table(aggregator):
    """
    Support SNMP tabular objects
    """
    instance = common.generate_instance_config(common.TABULAR_OBJECTS)
    check = common.create_check(instance)

    check.check(instance)

    # Test metrics
    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_table_regex_match(aggregator):
    metrics = [
        {
            'MIB': "IF-MIB",
            'table': "ifTable",
            'symbols': ["ifInOctets", "ifOutOctets"],
            'metric_tags': [
                {'tag': "interface", 'column': "ifDescr"},
                {'column': "ifDescr", 'match': '(\\w)(\\w+)', 'tags': {'prefix': '\\1', 'suffix': '\\2'}},
            ],
        }
    ]
    common_tags = ['snmp_device:localhost']

    instance = common.generate_instance_config(metrics)
    check = common.create_check(instance)

    check.check(instance)

    # Test metrics
    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        for interface in ['tunl0', 'eth0', 'ip6tnl0']:
            tags = common_tags + [
                'interface:{}'.format(interface),
                'prefix:{}'.format(interface[:1]),
                'suffix:{}'.format(interface[1:]),
            ]
            aggregator.assert_metric(metric_name, tags=tags)

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    common.assert_common_metrics(aggregator)
    aggregator.assert_all_metrics_covered()


def test_resolved_table(aggregator):
    instance = common.generate_instance_config(common.RESOLVED_TABULAR_OBJECTS)
    check = common.create_check(instance)

    check.check(instance)

    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_table_v3_MD5_DES(aggregator):
    """
    Support SNMP V3 priv modes: MD5 + DES
    """
    # build multiple confgs
    auth = 'MD5'
    priv = 'DES'
    name = 'instance_{}_{}'.format(auth, priv)

    instance = common.generate_v3_instance_config(
        common.TABULAR_OBJECTS,
        name=name,
        user='datadog{}{}'.format(auth.upper(), priv.upper()),
        auth=common.AUTH_PROTOCOLS[auth],
        auth_key=common.AUTH_KEY,
        priv=common.PRIV_PROTOCOLS[priv],
        priv_key=common.PRIV_KEY,
    )
    check = common.create_check(instance)

    check.check(instance)

    # Test metrics
    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_table_v3_MD5_AES(aggregator):
    """
    Support SNMP V3 priv modes: MD5 + AES
    """
    # build multiple confgs
    auth = 'MD5'
    priv = 'AES'
    name = 'instance_{}_{}'.format(auth, priv)

    instance = common.generate_v3_instance_config(
        common.TABULAR_OBJECTS,
        name=name,
        user='datadog{}{}'.format(auth.upper(), priv.upper()),
        auth=auth,
        auth_key=common.AUTH_KEY,
        priv=priv,
        priv_key=common.PRIV_KEY,
    )
    check = common.create_check(instance)

    check.check(instance)

    # Test metrics
    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_table_v3_SHA_DES(aggregator):
    """
    Support SNMP V3 priv modes: SHA + DES
    """
    # build multiple confgs
    auth = 'SHA'
    priv = 'DES'
    name = 'instance_{}_{}'.format(auth, priv)
    instance = common.generate_v3_instance_config(
        common.TABULAR_OBJECTS,
        name=name,
        user='datadog{}{}'.format(auth.upper(), priv.upper()),
        auth=auth,
        auth_key=common.AUTH_KEY,
        priv=priv,
        priv_key=common.PRIV_KEY,
    )
    check = common.create_check(instance)

    check.check(instance)

    # Test metrics
    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_table_v3_SHA_AES(aggregator):
    """
    Support SNMP V3 priv modes: SHA + AES
    """
    # build multiple confgs
    auth = 'SHA'
    priv = 'AES'
    name = 'instance_{}_{}'.format(auth, priv)
    instance = common.generate_v3_instance_config(
        common.TABULAR_OBJECTS,
        name=name,
        user='datadog{}{}'.format(auth.upper(), priv.upper()),
        auth=common.AUTH_PROTOCOLS[auth],
        auth_key=common.AUTH_KEY,
        priv=common.PRIV_PROTOCOLS[priv],
        priv_key=common.PRIV_KEY,
    )
    check = common.create_check(instance)

    check.check(instance)

    # Test metrics
    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_bulk_table(aggregator):
    instance = common.generate_instance_config(common.BULK_TABULAR_OBJECTS)
    instance['bulk_threshold'] = 5
    check = common.create_check(instance)

    check.check(instance)

    # Test metrics
    for symbol in common.BULK_TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.BULK_TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)

    for symbol in common.BULK_TABULAR_OBJECTS[1]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_invalid_metric(aggregator):
    """
    Invalid metrics raise a Warning and a critical service check
    """
    instance = common.generate_instance_config(common.INVALID_METRICS)
    check = common.create_check(instance)
    check.check(instance)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.WARNING, tags=common.CHECK_TAGS, at_least=1)


def test_forcedtype_metric(aggregator):
    """
    Forced Types should be reported as metrics of the forced type
    """
    instance = common.generate_instance_config(common.FORCED_METRICS)
    check = common.create_check(instance)
    check.check(instance)

    aggregator.assert_metric('snmp.IAmAGauge32', tags=common.CHECK_TAGS, count=1, metric_type=aggregator.RATE)
    aggregator.assert_metric('snmp.IAmACounter64', tags=common.CHECK_TAGS, count=1, metric_type=aggregator.GAUGE)
    aggregator.assert_metric(
        'snmp.IAmAOctetStringFloat', tags=common.CHECK_TAGS, value=3.1415, count=1, metric_type=aggregator.GAUGE
    )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_invalid_forcedtype_metric(aggregator, caplog):
    """
    If a forced type is invalid a warning should be issued
    but the check should continue processing the remaining metrics.
    """
    instance = common.generate_instance_config(common.INVALID_FORCED_METRICS)
    check = common.create_check(instance)

    check.check(instance)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    assert "Unable to submit metric" in caplog.text


def test_scalar_with_tags(aggregator):
    """
    Support SNMP scalar objects with tags
    """
    instance = common.generate_instance_config(common.SCALAR_OBJECTS_WITH_TAGS)
    check = common.create_check(instance)

    check.check(instance)

    # Test metrics
    for metric in common.SCALAR_OBJECTS_WITH_TAGS:
        metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
        tags = common.CHECK_TAGS + metric.get('metric_tags')
        aggregator.assert_metric(metric_name, tags=tags, count=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_network_failure(aggregator):
    """
    Network failure is reported in service check
    """
    instance = common.generate_instance_config(common.SCALAR_OBJECTS)

    # Change port so connection will fail
    instance['port'] = 162
    check = common.create_check(instance)

    check.check(instance)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.CRITICAL, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_cast_metrics(aggregator):
    instance = common.generate_instance_config(common.CAST_METRICS)
    check = common.create_check(instance)

    check.check(instance)
    aggregator.assert_metric('snmp.cpuload1', value=0.06)
    aggregator.assert_metric('snmp.cpuload2', value=0.06)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_profile(aggregator):
    instance = common.generate_instance_config([])
    instance['profile'] = 'profile1'
    init_config = {'profiles': {'profile1': {'definition': {'metrics': common.SUPPORTED_METRIC_TYPES}}}}
    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)

    common_tags = common.CHECK_TAGS + ['snmp_profile:profile1']
    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common_tags, count=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    common.assert_common_metrics(aggregator)
    aggregator.assert_all_metrics_covered()


def test_profile_by_file(aggregator):
    instance = common.generate_instance_config([])
    instance['profile'] = 'profile1'
    with temp_dir() as tmp:
        profile_file = os.path.join(tmp, 'profile1.yaml')
        with open(profile_file, 'w') as f:
            f.write(yaml.safe_dump({'metrics': common.SUPPORTED_METRIC_TYPES}))
        init_config = {'profiles': {'profile1': {'definition_file': profile_file}}}
        check = SnmpCheck('snmp', init_config, [instance])
        check.check(instance)

    common_tags = common.CHECK_TAGS + ['snmp_profile:profile1']
    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common_tags, count=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    common.assert_common_metrics(aggregator)
    aggregator.assert_all_metrics_covered()


def test_profile_sys_object(aggregator):
    instance = common.generate_instance_config([])
    init_config = {
        'profiles': {
            'profile1': {
                'definition': {'metrics': common.SUPPORTED_METRIC_TYPES, 'sysobjectid': '1.3.6.1.4.1.8072.3.2.10'}
            }
        }
    }
    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)
    common_tags = common.CHECK_TAGS + ['snmp_profile:profile1']

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common_tags, count=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    common.assert_common_metrics(aggregator)
    aggregator.assert_all_metrics_covered()


def test_profile_sysoid_list(aggregator, caplog):
    definition = {
        'metric_tags': [{'OID': '1.3.6.1.2.1.1.2', 'symbol': 'sysoid', 'tag': 'snmp_oid'}],
        'metrics': [{'OID': "1.3.6.1.2.1.7.1.0", 'name': "IAmACounter32"}],
        'sysobjectid': ['1.3.6.1.4.1.232.1.2', '1.3.6.1.4.1.1.2.1.3.4'],
    }
    init_config = {'profiles': {'profile1': {'definition': definition}}}

    devices_matched = [
        {'community_string': 'hpe-proliant', 'sysobjectid': '1.3.6.1.4.1.232.1.2'},
        {'community_string': 'network', 'sysobjectid': '1.3.6.1.4.1.1.2.1.3.4'},
    ]
    common_tags = common.CHECK_TAGS + ['snmp_profile:profile1']
    for device in devices_matched:
        instance = common.generate_instance_config([])
        instance['community_string'] = device['community_string']
        check = SnmpCheck('snmp', init_config, [instance])
        check.check(instance)

        tags = common_tags + ['snmp_oid:{}'.format(device['sysobjectid'])]
        aggregator.assert_metric('snmp.IAmACounter32', tags=tags, count=1)
        aggregator.assert_metric('snmp.devices_monitored', tags=tags, count=1, value=1)

        aggregator.assert_all_metrics_covered()

        aggregator.reset()

    caplog.at_level(logging.WARNING)
    devices_not_matched = [
        {'community_string': '3850', 'sysobjectid': '1.3.6.1.4.1.9.1.1745'},
    ]
    for device in devices_not_matched:
        instance = common.generate_instance_config([])
        instance['community_string'] = device['community_string']
        check = SnmpCheck('snmp', init_config, [instance])
        check.check(instance)

        assert 'No profile matching sysObjectID 1.3.6.1.4.1.9.1.1745' in caplog.text
        aggregator.assert_metric('snmp.devices_monitored', tags=common.CHECK_TAGS, count=1, value=1)

        aggregator.assert_all_metrics_covered()

        aggregator.reset()
        caplog.clear()


@pytest.mark.parametrize(
    'most_specific_oid, least_specific_oid',
    [
        pytest.param('1.3.6.1.4.1.8072.3.2.10', '1.3.6.1.4.1.5082.4', id='literal-literal'),
        pytest.param('1.3.6.1.4.1.8072.3.2.10', '1.3.6.1.4.1.8072.3.2.9', id='literal-literal-same-length'),
        pytest.param('1.3.6.1.4.1.8072.3.2.10', '1.3.6.1.4.1.*', id='literal-wildcard'),
        pytest.param('1.3.6.1.4.1.*', '1.3.6.1.4.1.2.3.4.5', id='wildcard-literal'),
        pytest.param('1.3.6.1.4.1.8072.3.2.*', '1.3.6.1.4.1.*', id='wildcard-wildcard'),
    ],
)
def test_profile_sys_object_prefix(aggregator, most_specific_oid, least_specific_oid):
    instance = common.generate_instance_config([])

    most_specific_profile = {'metrics': common.SUPPORTED_METRIC_TYPES, 'sysobjectid': most_specific_oid}
    least_specific_profile = {'metrics': common.CAST_METRICS, 'sysobjectid': least_specific_oid}

    init_config = {
        'profiles': {'most': {'definition': most_specific_profile}, 'least': {'definition': least_specific_profile}}
    }
    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)

    matching_profile_tags = common.CHECK_TAGS + ['snmp_profile:most']
    ignored_profile_tags = common.CHECK_TAGS + ['snmp_profile:least']

    for metric in most_specific_profile['metrics']:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=matching_profile_tags, count=1)

    for metric in least_specific_profile['metrics']:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=ignored_profile_tags, count=0)

    aggregator.assert_metric('snmp.sysUpTimeInstance', tags=matching_profile_tags, count=1)

    common.assert_common_metrics(aggregator)
    aggregator.assert_all_metrics_covered()


def test_profile_sys_object_unknown(aggregator, caplog):
    """If the fetched sysObjectID is not referenced by any profiles, check fails."""
    caplog.set_level(logging.WARNING)

    unknown_sysobjectid = '1.2.3.4.5'
    init_config = {
        'profiles': {
            'profile1': {'definition': {'metrics': common.SUPPORTED_METRIC_TYPES, 'sysobjectid': unknown_sysobjectid}}
        }
    }

    # Via config...

    instance = common.generate_instance_config([])
    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.CRITICAL, tags=common.CHECK_TAGS, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()

    # Via network discovery...

    host = socket.gethostbyname(common.HOST)
    network = ipaddress.ip_network(u'{}/29'.format(host), strict=False).with_prefixlen
    instance = {
        'name': 'snmp_conf',
        'network_address': network,
        'port': common.PORT,
        'community_string': 'public',
        'retries': 0,
        'discovery_interval': 0,
    }

    check = SnmpCheck('snmp', init_config, [instance])
    check._start_discovery()
    time.sleep(2)  # Give discovery a chance to fail finding a matching profile.
    check.check(instance)
    check._running = False
    check._thread.join()

    for record in caplog.records:
        if "Host {} didn't match a profile".format(host) in record.message:
            break
    else:
        pytest.fail()


def test_profile_sys_object_no_metrics():
    """If an instance is created without metrics and there is no profile defined, an error is raised."""
    instance = common.generate_instance_config([])
    with pytest.raises(ConfigurationError):
        SnmpCheck('snmp', {'profiles': {}}, [instance])


def test_discovery(aggregator):
    host = socket.gethostbyname(common.HOST)
    network = ipaddress.ip_network(u'{}/29'.format(host), strict=False).with_prefixlen
    check_tags = [
        'snmp_device:{}'.format(host),
        'snmp_profile:profile1',
        'autodiscovery_subnet:{}'.format(to_native_string(network)),
    ]
    instance = {
        'name': 'snmp_conf',
        # Make sure the check handles bytes
        'network_address': to_native_string(network),
        'port': common.PORT,
        'community_string': 'public',
        'retries': 0,
        'discovery_interval': 0,
    }
    init_config = {
        'profiles': {
            'profile1': {'definition': {'metrics': common.SUPPORTED_METRIC_TYPES, 'sysobjectid': '1.3.6.1.4.1.8072.*'}}
        }
    }
    check = SnmpCheck('snmp', init_config, [instance])
    try:
        for _ in range(30):
            check.check(instance)
            if len(aggregator.metric_names) > 1:
                break
            time.sleep(1)
            aggregator.reset()
    finally:
        check._running = False
        del check  # This is what the Agent would do when unscheduling the check.

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=check_tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance')
    aggregator.assert_metric('snmp.discovered_devices_count', tags=['network:{}'.format(network)])

    aggregator.assert_metric('snmp.devices_monitored', metric_type=aggregator.GAUGE, tags=check_tags)
    aggregator.assert_all_metrics_covered()


@mock.patch("datadog_checks.snmp.snmp.read_persistent_cache")
def test_discovery_devices_monitored_count(read_mock, aggregator):
    read_mock.return_value = '["192.168.0.1","192.168.0.2"]'

    host = socket.gethostbyname(common.HOST)
    network = ipaddress.ip_network(u'{}/29'.format(host), strict=False).with_prefixlen
    check_tags = [
        'autodiscovery_subnet:{}'.format(to_native_string(network)),
    ]
    instance = {
        'name': 'snmp_conf',
        # Make sure the check handles bytes
        'network_address': to_native_string(network),
        'port': common.PORT,
        'community_string': 'public',
        'retries': 0,
        'discovery_interval': 0,
    }
    init_config = {
        'profiles': {
            'profile1': {'definition': {'metrics': common.SUPPORTED_METRIC_TYPES, 'sysobjectid': '1.3.6.1.4.1.8072.*'}}
        }
    }
    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)
    check._running = False

    aggregator.assert_metric('snmp.discovered_devices_count', tags=['network:{}'.format(network)])

    for device_ip in ['192.168.0.1', '192.168.0.2']:
        tags = check_tags + ['snmp_device:{}'.format(device_ip)]
        aggregator.assert_metric('snmp.devices_monitored', metric_type=aggregator.GAUGE, value=1, count=1, tags=tags)
    aggregator.assert_all_metrics_covered()


def test_different_mibs(aggregator):
    metrics = [
        {
            'MIB': 'ENTITY-SENSOR-MIB',
            'table': 'entitySensorObjects',
            'symbols': ['entPhySensorValue'],
            'metric_tags': [
                {'tag': 'desc', 'column': 'entLogicalDescr', 'table': 'entLogicalTable', 'MIB': 'ENTITY-MIB'}
            ],
        }
    ]
    instance = common.generate_instance_config(metrics)
    instance['community_string'] = 'entity'
    check = common.create_check(instance)

    check.check(instance)
    aggregator.assert_metric_has_tag_prefix('snmp.entPhySensorValue', 'desc')


def test_different_tables(aggregator):
    metrics = [
        {
            'MIB': 'IF-MIB',
            'table': 'ifTable',
            'symbols': ['ifInOctets', 'ifOutOctets'],
            'metric_tags': [
                {'tag': 'interface', 'column': 'ifDescr'},
                {'tag': 'speed', 'column': 'ifHighSpeed', 'table': 'ifXTable'},
            ],
        }
    ]
    instance = common.generate_instance_config(metrics)
    instance['community_string'] = 'if'
    # Enforce bulk to trigger table usage
    instance['bulk_threshold'] = 1
    instance['enforce_mib_constraints'] = False
    check = common.create_check(instance)

    check.check(instance)
    aggregator.assert_metric_has_tag_prefix('snmp.ifInOctets', 'speed')


def test_metric_tag_symbol(aggregator):
    metrics = common.SUPPORTED_METRIC_TYPES
    instance = common.generate_instance_config(metrics)
    instance['metric_tags'] = [{'MIB': 'SNMPv2-MIB', 'symbol': 'sysName', 'tag': 'snmp_host'}]
    check = common.create_check(instance)

    check.check(instance)

    tags = list(common.CHECK_TAGS)
    tags.append('snmp_host:41ba948911b9')

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=tags, count=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=tags, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_metric_tag_oid(aggregator):
    metrics = common.SUPPORTED_METRIC_TYPES
    instance = common.generate_instance_config(metrics)
    instance['metric_tags'] = [{'OID': '1.3.6.1.2.1.1.5.0', 'symbol': 'sysName', 'tag': 'snmp_host'}]
    check = common.create_check(instance)

    check.check(instance)

    tags = list(common.CHECK_TAGS)
    tags.append('snmp_host:41ba948911b9')

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=tags, count=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=tags, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_metric_tag_profile_manual(aggregator):
    instance = common.generate_instance_config([])
    instance['profile'] = 'profile1'
    definition = {
        'metric_tags': [{'OID': '1.3.6.1.2.1.1.5.0', 'symbol': 'sysName', 'tag': 'snmp_host'}],
        'metrics': common.SUPPORTED_METRIC_TYPES,
    }
    init_config = {'profiles': {'profile1': {'definition': definition}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    tags = list(common.CHECK_TAGS)
    tags.append('snmp_host:41ba948911b9')
    tags.append('snmp_profile:profile1')

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=tags, count=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=tags, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_metric_tag_profile_sysoid(aggregator):
    instance = common.generate_instance_config([])
    definition = {
        'metric_tags': [{'OID': '1.3.6.1.2.1.1.5.0', 'symbol': 'sysName', 'tag': 'snmp_host'}],
        'metrics': common.SUPPORTED_METRIC_TYPES,
        'sysobjectid': '1.3.6.1.4.1.8072.3.2.10',
    }
    init_config = {'profiles': {'profile1': {'definition': definition}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    tags = list(common.CHECK_TAGS)
    tags.append('snmp_host:41ba948911b9')
    tags.append('snmp_profile:profile1')

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=tags, count=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=tags, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_metric_tags_misconfiguration():
    metrics = common.SUPPORTED_METRIC_TYPES
    instance = common.generate_instance_config(metrics)

    instance['metric_tags'] = [{'OID': '1.3.6.1.2.1.1.5.0', 'tag': 'snmp_host'}]
    with pytest.raises(ConfigurationError):
        common.create_check(instance)

    instance['metric_tags'] = [{'OID': '1.3.6.1.2.1.1.5.0', 'symbol': 'sysName'}]
    with pytest.raises(ConfigurationError):
        common.create_check(instance)

    instance['metric_tags'] = [{'tag': 'sysName', 'symbol': 'sysName'}]
    with pytest.raises(ConfigurationError):
        common.create_check(instance)

    instance['metric_tags'] = [{'tags': {'foo': 'bar'}, 'symbol': 'sysName', 'MIB': 'SNMPv2-MIB'}]
    with pytest.raises(ConfigurationError):
        common.create_check(instance)

    instance['metric_tags'] = [{'tags': 'foo', 'match': 'bar', 'symbol': 'sysName', 'MIB': 'SNMPv2-MIB'}]
    with pytest.raises(ConfigurationError):
        common.create_check(instance)

    instance['metric_tags'] = [{'tags': {'foo': 'bar'}, 'match': '(', 'symbol': 'sysName', 'MIB': 'SNMPv2-MIB'}]
    with pytest.raises(ConfigurationError):
        common.create_check(instance)


def test_metric_tag_multiple(aggregator, caplog):
    metrics = common.SUPPORTED_METRIC_TYPES
    instance = common.generate_instance_config(metrics)
    instance['metric_tags'] = [
        {'MIB': 'SNMPv2-MIB', 'symbol': 'sysName', 'tag': 'snmp_host'},
        {'MIB': 'IF-MIB', 'symbol': 'ifOutOctets', 'tag': 'out'},
    ]
    check = common.create_check(instance)

    with caplog.at_level(logging.WARNING):
        check.check(instance)

    expected_message = (
        'You are trying to use a table column (OID `{}`) as a metric tag. This is not supported as '
        '`metric_tags` can only refer to scalar OIDs.'.format(instance['metric_tags'][1]['symbol'])
    )
    for _, level, message in caplog.record_tuples:
        if level == logging.WARNING and message == expected_message:
            break
    else:
        raise AssertionError('Expected WARNING log with message `{}`'.format(expected_message))


def test_metric_tag_matching(aggregator):
    metrics = common.SUPPORTED_METRIC_TYPES
    instance = common.generate_instance_config(metrics)
    instance['metric_tags'] = [
        {
            'MIB': 'SNMPv2-MIB',
            'symbol': 'sysName',
            'match': '(\\d\\d)(.*)',
            'tags': {'host_prefix': '\\1', 'host': '\\2'},
        }
    ]
    check = common.create_check(instance)

    check.check(instance)

    tags = list(common.CHECK_TAGS)
    tags.append('host:ba948911b9')
    tags.append('host_prefix:41')

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=tags, count=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=tags, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


def test_timeout(aggregator, caplog):
    caplog.set_level(logging.WARNING)

    instance = common.generate_instance_config([])
    instance['community_string'] = 'public_delay'
    instance['timeout'] = 1
    instance['retries'] = 0
    check = SnmpCheck('snmp', {}, [instance])
    check.check(instance)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.WARNING, at_least=1)
    # Some metrics still arrived
    aggregator.assert_metric('snmp.ifInDiscards', count=4)
    aggregator.assert_metric('snmp.ifInErrors', count=4)
    aggregator.assert_metric('snmp.ifOutDiscards', count=4)
    aggregator.assert_metric('snmp.ifOutErrors', count=4)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()

    for record in caplog.records:
        if "No SNMP response received before timeout" in record.message:
            break
    else:
        pytest.fail()


def test_oids_cache_metrics_collected_using_scalar_oids(aggregator):
    """
    Test if we still collect all metrics using saved scalar oids.
    """
    instance = common.generate_instance_config(common.TABULAR_OBJECTS)
    instance['refresh_oids_cache_interval'] = 3600
    check = common.create_check(instance)

    def run_check():
        aggregator.reset()
        check.check(instance)

        # Test metrics
        for symbol in common.TABULAR_OBJECTS[0]['symbols']:
            metric_name = "snmp." + symbol
            aggregator.assert_metric(metric_name, at_least=1)
            aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

            for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
                tag = mtag['tag']
                aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)
        aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

        # Test service check
        aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

        common.assert_common_metrics(aggregator)
        aggregator.all_metrics_asserted()

    for _ in range(3):
        run_check()


@pytest.mark.parametrize(
    "config, has_next_bulk_oids",
    [
        pytest.param({}, True, id='disabled_config_default'),
        pytest.param({'refresh_oids_cache_interval': 0}, True, id='disabled_config_explicit'),
        pytest.param({'refresh_oids_cache_interval': 60}, False, id='enabled_config_60'),
        pytest.param({'refresh_oids_cache_interval': 3600}, False, id='enabled_config_3600'),
    ],
)
def test_oids_cache_config_update(config, has_next_bulk_oids):
    """
    Check whether config oids are correctly updated depending on refresh_oids_cache_interval.
    """
    instance = common.generate_instance_config(common.BULK_TABULAR_OBJECTS)
    instance['bulk_threshold'] = 10
    instance.update(config)
    check = common.create_check(instance)

    assert bool(check._config.oid_config.scalar_oids) is False
    assert bool(check._config.oid_config.next_oids) is True
    assert bool(check._config.oid_config.bulk_oids) is True

    for _ in range(3):
        check.check(instance)
        assert bool(check._config.oid_config.scalar_oids) is True
        assert bool(check._config.oid_config.next_oids) is has_next_bulk_oids
        assert bool(check._config.oid_config.bulk_oids) is has_next_bulk_oids


GETNEXT_CALL_COUNT_PER_CHECK_RUN = 5


@pytest.mark.parametrize(
    "refresh_interval, getnext_call_counts, getnext_call_count_after_reset",
    [
        # When the cache is enabled.
        # GETNEXT calls are made only at the first check and run and after every reset
        pytest.param(
            3600,
            [GETNEXT_CALL_COUNT_PER_CHECK_RUN, GETNEXT_CALL_COUNT_PER_CHECK_RUN, GETNEXT_CALL_COUNT_PER_CHECK_RUN],
            2 * GETNEXT_CALL_COUNT_PER_CHECK_RUN,
            id='cache_enabled',
        ),
        # When the cache is disabled.
        # GETNEXT calls are made only at the first check and run and after every reset
        pytest.param(
            0,
            [
                1 * GETNEXT_CALL_COUNT_PER_CHECK_RUN,
                2 * GETNEXT_CALL_COUNT_PER_CHECK_RUN,
                3 * GETNEXT_CALL_COUNT_PER_CHECK_RUN,
            ],
            4 * GETNEXT_CALL_COUNT_PER_CHECK_RUN,
            id='cache_disabled',
        ),
    ],
)
def test_oids_cache_command_calls(refresh_interval, getnext_call_counts, getnext_call_count_after_reset):
    """
    Check that less snmp PDU calls are made using `refresh_oids_cache_interval` config.
    """
    instance = common.generate_instance_config(common.BULK_TABULAR_OBJECTS)
    instance['refresh_oids_cache_interval'] = refresh_interval
    check = common.create_check(instance)

    with mock.patch('datadog_checks.snmp.snmp.snmp_getnext') as snmp_getnext:
        assert snmp_getnext.call_count == 0
        for call_count in getnext_call_counts:
            check.check(instance)
            assert snmp_getnext.call_count == call_count

        check._config.oid_config._last_ts = 0
        check.check(instance)
        assert snmp_getnext.call_count == getnext_call_count_after_reset
