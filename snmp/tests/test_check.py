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

from datadog_checks import snmp
from datadog_checks.base import ConfigurationError
from datadog_checks.dev import temp_dir
from datadog_checks.snmp import SnmpCheck

from . import common

pytestmark = pytest.mark.usefixtures("dd_environment")


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

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    aggregator.all_metrics_asserted()


def test_transient_error(aggregator):
    instance = common.generate_instance_config(common.SUPPORTED_METRIC_TYPES)
    check = common.create_check(instance)

    with mock.patch.object(check, 'raise_on_error_indication', side_effect=RuntimeError):
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

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    aggregator.all_metrics_asserted()


def test_snmp_getnext_call():
    instance = common.generate_instance_config(common.PLAY_WITH_GET_NEXT_METRICS)
    instance['snmp_version'] = 1
    check = common.create_check(instance)

    # Test that we invoke next with the correct keyword arguments that are hard to test otherwise
    with mock.patch("datadog_checks.snmp.snmp.hlapi.nextCmd") as nextCmd:

        check.check(instance)
        _, kwargs = nextCmd.call_args
        assert ("ignoreNonIncreasingOid", False) in kwargs.items()
        assert ("lexicographicMode", False) in kwargs.items()

        check = SnmpCheck('snmp', common.IGNORE_NONINCREASING_OID, [instance])
        check.check(instance)
        _, kwargs = nextCmd.call_args
        assert ("ignoreNonIncreasingOid", True) in kwargs.items()
        assert ("lexicographicMode", False) in kwargs.items()


def test_custom_mib(aggregator):
    instance = common.generate_instance_config(common.DUMMY_MIB_OID)
    instance["community_string"] = "dummy"

    check = SnmpCheck('snmp', common.MIBS_FOLDER, [instance])
    check.check(instance)

    # Test metrics
    for metric in common.DUMMY_MIB_OID:
        metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, at_least=1)

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

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

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

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    aggregator.all_metrics_asserted()


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

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

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

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

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

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

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

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

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

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

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

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    aggregator.all_metrics_asserted()


def test_invalid_metric(aggregator):
    """
    Invalid metrics raise a Warning and a critical service check
    """
    instance = common.generate_instance_config(common.INVALID_METRICS)
    check = common.create_check(instance)
    check.check(instance)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.CRITICAL, tags=common.CHECK_TAGS, at_least=1)


def test_forcedtype_metric(aggregator):
    """
    Forced Types should be reported as metrics of the forced type
    """
    instance = common.generate_instance_config(common.FORCED_METRICS)
    check = common.create_check(instance)
    check.check(instance)

    for metric in common.FORCED_METRICS:
        metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
        if metric.get('forced_type') == 'counter':
            # rate will be flushed as a gauge, so count should be 0.
            aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=0, metric_type=aggregator.GAUGE)
        elif metric.get('forced_type') == 'gauge':
            aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, at_least=1, metric_type=aggregator.GAUGE)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    aggregator.all_metrics_asserted()


def test_invalid_forcedtype_metric(aggregator):
    """
    If a forced type is invalid a warning should be issued + a service check
    should be available
    """
    instance = common.generate_instance_config(common.INVALID_FORCED_METRICS)
    check = common.create_check(instance)

    check.check(instance)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.WARNING, tags=common.CHECK_TAGS, at_least=1)


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

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

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

    aggregator.all_metrics_asserted()


def test_cast_metrics(aggregator):
    instance = common.generate_instance_config(common.CAST_METRICS)
    check = common.create_check(instance)

    check.check(instance)
    aggregator.assert_metric('snmp.cpuload1', value=0.06)
    aggregator.assert_metric('snmp.cpuload2', value=0.06)

    aggregator.all_metrics_asserted()


def test_profile(aggregator):
    instance = common.generate_instance_config([])
    instance['profile'] = 'profile1'
    init_config = {'profiles': {'profile1': {'definition': {'metrics': common.SUPPORTED_METRIC_TYPES}}}}
    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=1)
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

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=1)
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

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=1)
    aggregator.assert_all_metrics_covered()


def test_profile_sys_object_prefix(aggregator):
    instance = common.generate_instance_config([])
    init_config = {
        'profiles': {
            'profile1': {
                'definition': {'metrics': common.SUPPORTED_METRIC_TYPES, 'sysobjectid': '1.3.6.1.4.1.8072.3.2.10'}
            },
            'profile2': {'definition': {'metrics': common.CAST_METRICS, 'sysobjectid': '1.3.6.1.4.*'}},
        }
    }
    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=1)
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
    aggregator.all_metrics_asserted()

    # Via network discovery...

    host = socket.gethostbyname(common.HOST)
    network = ipaddress.ip_network(u'{}/29'.format(host), strict=False).with_prefixlen
    instance = {
        'name': 'snmp_conf',
        'network_address': network,
        'port': common.PORT,
        'community_string': 'public',
    }

    check = SnmpCheck('snmp', init_config, [instance])
    check._start_discovery()
    time.sleep(2)  # Give discovery a chance to fail finding a matching profile.
    check.check(instance)

    for record in caplog.records:
        if "Host {} didn't match a profile".format(host) in record.message:
            break
    else:
        pytest.fail()


def test_profile_sys_object_no_metrics():
    """If an instance is created without metrics and there is no profile defined, an error is raised."""
    instance = common.generate_instance_config([])
    with pytest.raises(ConfigurationError):
        SnmpCheck('snmp', {}, [instance])


def test_discovery(aggregator):
    host = socket.gethostbyname(common.HOST)
    network = ipaddress.ip_network(u'{}/29'.format(host), strict=False).with_prefixlen
    check_tags = ['snmp_device:{}'.format(host)]
    instance = {
        'name': 'snmp_conf',
        # Make sure the check handles bytes
        'network_address': network.encode('utf-8'),
        'port': common.PORT,
        'community_string': 'public',
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

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=check_tags, count=1)

    aggregator.assert_metric('snmp.discovered_devices_count', tags=['network:{}'.format(network)])
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


def test_f5(aggregator):
    instance = common.generate_instance_config([])
    # We need the full path as we're not in installed mode
    path = os.path.join(os.path.dirname(snmp.__file__), 'data', 'profiles', 'f5-big-ip.yaml')
    instance['community_string'] = 'f5'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'f5-big-ip': {'definition_file': path}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    gauges = [
        'sysStatMemoryTotal',
        'sysStatMemoryUsed',
        'sysGlobalTmmStatMemoryTotal',
        'sysGlobalTmmStatMemoryUsed',
        'sysGlobalHostOtherMemoryTotal',
        'sysGlobalHostOtherMemoryUsed',
        'sysGlobalHostSwapTotal',
        'sysGlobalHostSwapUsed',
        'sysTcpStatOpen',
        'sysTcpStatCloseWait',
        'sysTcpStatFinWait',
        'sysTcpStatTimeWait',
        'sysUdpStatOpen',
        'sysClientsslStatCurConns',
    ]
    counts = [
        'sysTcpStatAccepts',
        'sysTcpStatAcceptfails',
        'sysTcpStatConnects',
        'sysTcpStatConnfails',
        'sysUdpStatAccepts',
        'sysUdpStatAcceptfails',
        'sysUdpStatConnects',
        'sysUdpStatConnfails',
        'sysClientsslStatEncryptedBytesIn',
        'sysClientsslStatEncryptedBytesOut',
        'sysClientsslStatDecryptedBytesIn',
        'sysClientsslStatDecryptedBytesOut',
        'sysClientsslStatHandshakeFailures',
    ]
    cpu_rates = [
        'sysMultiHostCpuUser',
        'sysMultiHostCpuNice',
        'sysMultiHostCpuSystem',
        'sysMultiHostCpuIdle',
        'sysMultiHostCpuIrq',
        'sysMultiHostCpuSoftirq',
        'sysMultiHostCpuIowait',
    ]
    if_gauges = ['ifAdminStatus', 'ifOperStatus']
    if_counts = ['ifHCInOctets', 'ifInErrors', 'ifHCOutOctets', 'ifOutErrors']
    interfaces = ['1.0', 'mgmt', '/Common/internal', '/Common/http-tunnel', '/Common/socks-tunnel']
    for metric in gauges:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1
        )
    for metric in counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common.CHECK_TAGS, count=1
        )
    for metric in cpu_rates:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=['cpu:0'] + common.CHECK_TAGS, count=1
        )
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=['cpu:1'] + common.CHECK_TAGS, count=1
        )
    for metric in if_counts:
        for interface in interfaces:
            aggregator.assert_metric(
                'snmp.{}'.format(metric),
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=['interface:{}'.format(interface)] + common.CHECK_TAGS,
                count=1,
            )
    for metric in if_gauges:
        for interface in interfaces:
            aggregator.assert_metric(
                'snmp.{}'.format(metric),
                metric_type=aggregator.GAUGE,
                tags=['interface:{}'.format(interface)] + common.CHECK_TAGS,
                count=1,
            )
    aggregator.assert_all_metrics_covered()


def test_router(aggregator):
    instance = common.generate_instance_config([])
    # We need the full path as we're not in installed mode
    path = os.path.join(os.path.dirname(snmp.__file__), 'data', 'profiles', 'generic-router.yaml')
    instance['community_string'] = 'network'
    instance['profile'] = 'router'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'router': {'definition_file': path}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    tcp_counts = [
        'tcpActiveOpens',
        'tcpPassiveOpens',
        'tcpAttemptFails',
        'tcpEstabResets',
        'tcpHCInSegs',
        'tcpHCOutSegs',
        'tcpRetransSegs',
        'tcpInErrs',
        'tcpOutRsts',
    ]
    tcp_gauges = ['tcpCurrEstab']
    udp_counts = ['udpHCInDatagrams', 'udpNoPorts', 'udpInErrors', 'udpHCOutDatagrams']
    if_counts = [
        'ifInErrors',
        'ifInDiscards',
        'ifOutErrors',
        'ifOutDiscards',
        'ifHCInOctets',
        'ifHCInUcastPkts',
        'ifHCInMulticastPkts',
        'ifHCInBroadcastPkts',
        'ifHCOutOctets',
        'ifHCOutUcastPkts',
        'ifHCOutMulticastPkts',
        'ifHCOutBroadcastPkts',
    ]
    if_gauges = ['ifAdminStatus', 'ifOperStatus']
    ip_counts = [
        'ipSystemStatsHCInReceives',
        'ipSystemStatsHCInOctets',
        'ipSystemStatsInHdrErrors',
        'ipSystemStatsInNoRoutes',
        'ipSystemStatsInAddrErrors',
        'ipSystemStatsInUnknownProtos',
        'ipSystemStatsInTruncatedPkts',
        'ipSystemStatsHCInForwDatagrams',
        'ipSystemStatsReasmReqds',
        'ipSystemStatsReasmOKs',
        'ipSystemStatsReasmFails',
        'ipSystemStatsInDiscards',
        'ipSystemStatsHCInDelivers',
        'ipSystemStatsHCOutRequests',
        'ipSystemStatsOutNoRoutes',
        'ipSystemStatsHCOutForwDatagrams',
        'ipSystemStatsOutDiscards',
        'ipSystemStatsOutFragReqds',
        'ipSystemStatsOutFragOKs',
        'ipSystemStatsOutFragFails',
        'ipSystemStatsOutFragCreates',
        'ipSystemStatsHCOutTransmits',
        'ipSystemStatsHCOutOctets',
        'ipSystemStatsHCInMcastPkts',
        'ipSystemStatsHCInMcastOctets',
        'ipSystemStatsHCOutMcastPkts',
        'ipSystemStatsHCOutMcastOctets',
        'ipSystemStatsHCInBcastPkts',
        'ipSystemStatsHCOutBcastPkts',
    ]
    ip_if_counts = [
        'ipIfStatsHCInOctets',
        'ipIfStatsInHdrErrors',
        'ipIfStatsInNoRoutes',
        'ipIfStatsInAddrErrors',
        'ipIfStatsInUnknownProtos',
        'ipIfStatsInTruncatedPkts',
        'ipIfStatsHCInForwDatagrams',
        'ipIfStatsReasmReqds',
        'ipIfStatsReasmOKs',
        'ipIfStatsReasmFails',
        'ipIfStatsInDiscards',
        'ipIfStatsHCInDelivers',
        'ipIfStatsHCOutRequests',
        'ipIfStatsHCOutForwDatagrams',
        'ipIfStatsOutDiscards',
        'ipIfStatsOutFragReqds',
        'ipIfStatsOutFragOKs',
        'ipIfStatsOutFragFails',
        'ipIfStatsOutFragCreates',
        'ipIfStatsHCOutTransmits',
        'ipIfStatsHCOutOctets',
        'ipIfStatsHCInMcastPkts',
        'ipIfStatsHCInMcastOctets',
        'ipIfStatsHCOutMcastPkts',
        'ipIfStatsHCOutMcastOctets',
        'ipIfStatsHCInBcastPkts',
        'ipIfStatsHCOutBcastPkts',
    ]
    for interface in ['eth0', 'eth1']:
        tags = ['interface:{}'.format(interface)] + common.CHECK_TAGS
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for metric in tcp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common.CHECK_TAGS, count=1
        )
    for metric in tcp_gauges:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1
        )
    for metric in udp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common.CHECK_TAGS, count=1
        )
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common.CHECK_TAGS
        for metric in ip_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in ip_if_counts:
            for interface in ['17', '21']:
                tags = ['ipversion:{}'.format(version), 'interface:{}'.format(interface)] + common.CHECK_TAGS
                aggregator.assert_metric(
                    'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
                )

    aggregator.assert_all_metrics_covered()


def test_f5_router(aggregator):
    instance = common.generate_instance_config([])
    # We need the full path as we're not in installed mode
    path = os.path.join(os.path.dirname(snmp.__file__), 'data', 'profiles', 'generic-router.yaml')

    # Use the generic profile against the f5 device
    instance['community_string'] = 'f5'
    instance['profile'] = 'router'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'router': {'definition_file': path}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    if_counts = [
        'ifInErrors',
        'ifInDiscards',
        'ifOutErrors',
        'ifOutDiscards',
        'ifHCInOctets',
        'ifHCInUcastPkts',
        'ifHCInMulticastPkts',
        'ifHCInBroadcastPkts',
        'ifHCOutOctets',
        'ifHCOutUcastPkts',
        'ifHCOutMulticastPkts',
        'ifHCOutBroadcastPkts',
    ]
    if_gauges = ['ifAdminStatus', 'ifOperStatus']
    # We only get a subset of metrics
    ip_counts = [
        'ipSystemStatsHCInReceives',
        'ipSystemStatsInHdrErrors',
        'ipSystemStatsOutFragReqds',
        'ipSystemStatsOutFragFails',
        'ipSystemStatsHCOutTransmits',
        'ipSystemStatsReasmReqds',
        'ipSystemStatsHCInMcastPkts',
        'ipSystemStatsReasmFails',
        'ipSystemStatsHCOutMcastPkts',
    ]
    interfaces = ['1.0', 'mgmt', '/Common/internal', '/Common/http-tunnel', '/Common/socks-tunnel']
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common.CHECK_TAGS
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common.CHECK_TAGS
        for metric in ip_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    aggregator.assert_all_metrics_covered()


def test_3850(aggregator):
    instance = common.generate_instance_config([])
    # We need the full path as we're not in installed mode
    path = os.path.join(os.path.dirname(snmp.__file__), 'data', 'profiles', 'cisco-3850.yaml')
    instance['community_string'] = '3850'
    instance['profile'] = 'cisco-3850'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'cisco-3850': {'definition_file': path}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    tcp_counts = [
        'tcpActiveOpens',
        'tcpPassiveOpens',
        'tcpAttemptFails',
        'tcpEstabResets',
        'tcpHCInSegs',
        'tcpHCOutSegs',
        'tcpRetransSegs',
        'tcpInErrs',
        'tcpOutRsts',
    ]
    tcp_gauges = ['tcpCurrEstab']
    udp_counts = ['udpHCInDatagrams', 'udpNoPorts', 'udpInErrors', 'udpHCOutDatagrams']
    if_counts = ['ifInErrors', 'ifInDiscards', 'ifOutErrors', 'ifOutDiscards']
    ifx_counts = [
        'ifHCInOctets',
        'ifHCInUcastPkts',
        'ifHCInMulticastPkts',
        'ifHCInBroadcastPkts',
        'ifHCOutOctets',
        'ifHCOutUcastPkts',
        'ifHCOutMulticastPkts',
        'ifHCOutBroadcastPkts',
    ]
    if_gauges = ['ifAdminStatus', 'ifOperStatus']
    # We're not covering all interfaces
    interfaces = ["GigabitEthernet1/0/{}".format(i) for i in range(1, 48)]
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common.CHECK_TAGS
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    interfaces = ["Gi1/0/{}".format(i) for i in range(1, 48)]
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common.CHECK_TAGS
        for metric in ifx_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
    for metric in tcp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common.CHECK_TAGS, count=1
        )
    for metric in tcp_gauges:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1
        )
    for metric in udp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common.CHECK_TAGS, count=1
        )
    sensors = [1006, 1007, 1008, 2006, 2007, 2008]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:8'] + common.CHECK_TAGS
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=1)
    fru_metrics = ["cefcFRUPowerAdminStatus", "cefcFRUPowerOperStatus", "cefcFRUCurrent"]
    frus = [1001, 1010, 2001, 2010]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common.CHECK_TAGS
        for metric in fru_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [1000, 2000]
    cpu_metrics = ["cpmCPUTotalMonIntervalValue", "cpmCPUMemoryUsed", "cpmCPUMemoryFree"]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common.CHECK_TAGS
        for metric in cpu_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    cie_metrics = ["cieIfLastInTime", "cieIfLastOutTime", "cieIfInputQueueDrops", "cieIfOutputQueueDrops"]
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common.CHECK_TAGS
        for metric in cie_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_meraki_cloud_controller(aggregator):
    instance = common.generate_instance_config([])
    path = os.path.join(os.path.dirname(snmp.__file__), 'data', 'profiles', 'meraki-cloud-controller.yaml')
    instance['community_string'] = 'meraki-cloud-controller'
    instance['profile'] = 'meraki'
    instance['enforce_mib_constraints'] = False
    init_config = {'profiles': {'meraki': {'definition_file': path}}}

    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)

    dev_metrics = ['devStatus', 'devClientCount']
    dev_tags = ['device:Gymnasium', 'product:MR16-HW', 'network:L_NETWORK'] + common.CHECK_TAGS
    for metric in dev_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=dev_tags, count=1)

    if_tags = ['interface:wifi0', 'index:4'] + common.CHECK_TAGS
    if_metrics = ['devInterfaceSentPkts', 'devInterfaceRecvPkts', 'devInterfaceSentBytes', 'devInterfaceSentBytes']
    for metric in if_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)


def test_idrac(aggregator):
    instance = common.generate_instance_config([])
    # We need the full path as we're not in installed mode
    path = os.path.join(os.path.dirname(snmp.__file__), 'data', 'profiles', 'idrac.yaml')
    instance['community_string'] = 'idrac'
    instance['profile'] = 'idrac'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'idrac': {'definition_file': path}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    if_counts = [
        'adapterRxPackets',
        'adapterTxPackets',
        'adapterRxBytes',
        'adapterTxBytes',
        'adapterRxErrors',
        'adapterTxErrors',
        'adapterRxDropped',
        'adapterTxDropped',
        'adapterRxMulticast',
        'adapterCollisions',
    ]
    status_gauges = [
        'systemStateChassisStatus',
        'systemStatePowerUnitStatusRedundancy',
        'systemStatePowerSupplyStatusCombined',
        'systemStateAmperageStatusCombined',
        'systemStateCoolingUnitStatusRedundancy',
        'systemStateCoolingDeviceStatusCombined',
        'systemStateTemperatureStatusCombined',
        'systemStateMemoryDeviceStatusCombined',
        'systemStateChassisIntrusionStatusCombined',
        'systemStatePowerUnitStatusCombined',
        'systemStateCoolingUnitStatusCombined',
        'systemStateProcessorDeviceStatusCombined',
        'systemStateTemperatureStatisticsStatusCombined',
    ]
    disk_gauges = [
        'physicalDiskState',
        'physicalDiskCapacityInMB',
        'physicalDiskUsedSpaceInMB',
        'physicalDiskFreeSpaceInMB',
    ]
    interfaces = ['eth0', 'en1']
    for interface in interfaces:
        tags = ['adapter:{}'.format(interface)] + common.CHECK_TAGS
        for count in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(count), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
    indexes = ['26', '29']
    for index in indexes:
        tags = ['chassis_index:{}'.format(index)] + common.CHECK_TAGS
        for gauge in status_gauges:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)
    powers = ['supply1', 'supply2']
    for power in powers:
        tags = ['supply_name:{}'.format(power)] + common.CHECK_TAGS
        aggregator.assert_metric('snmp.enclosurePowerSupplyState', metric_type=aggregator.GAUGE, tags=tags, count=1)
    disks = ['disk1', 'disk2']
    for disk in disks:
        tags = ['disk_name:{}'.format(disk)] + common.CHECK_TAGS
        for gauge in disk_gauges:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_cisco_nexus(aggregator):
    instance = common.generate_instance_config([])
    instance['community_string'] = 'cisco_nexus'
    instance['profile'] = 'cisco-nexus'
    instance['enforce_mib_constraints'] = False

    # We need the full path as we're not in installed mode
    definition_file_path = os.path.join(os.path.dirname(snmp.__file__), 'data', 'profiles', 'cisco-nexus.yaml')
    init_config = {'profiles': {'cisco-nexus': {'definition_file': definition_file_path}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    tcp_counts = [
        'tcpActiveOpens',
        'tcpPassiveOpens',
        'tcpAttemptFails',
        'tcpEstabResets',
        'tcpHCInSegs',
        'tcpHCOutSegs',
        'tcpRetransSegs',
        'tcpInErrs',
        'tcpOutRsts',
    ]
    tcp_gauges = ['tcpCurrEstab']
    udp_counts = ['udpHCInDatagrams', 'udpNoPorts', 'udpInErrors', 'udpHCOutDatagrams']
    if_counts = ['ifInErrors', 'ifInDiscards', 'ifOutErrors', 'ifOutDiscards']
    ifx_counts = [
        'ifHCInOctets',
        'ifHCInUcastPkts',
        'ifHCInMulticastPkts',
        'ifHCInBroadcastPkts',
        'ifHCOutOctets',
        'ifHCOutUcastPkts',
        'ifHCOutMulticastPkts',
        'ifHCOutBroadcastPkts',
    ]
    if_gauges = ['ifAdminStatus', 'ifOperStatus']

    interfaces = ["GigabitEthernet1/0/{}".format(i) for i in range(1, 9)]

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common.CHECK_TAGS
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common.CHECK_TAGS
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common.CHECK_TAGS
        for metric in ifx_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    for metric in tcp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common.CHECK_TAGS, count=1
        )

    for metric in tcp_gauges:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1
        )

    for metric in udp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common.CHECK_TAGS, count=1
        )

    sensors = [1, 9, 11, 12, 12, 14, 17, 26, 29, 31]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:8'] + common.CHECK_TAGS
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=1)

    fru_metrics = ["cefcFRUPowerAdminStatus", "cefcFRUPowerOperStatus", "cefcFRUCurrent"]
    frus = [6, 7, 15, 16, 19, 27, 30, 31]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common.CHECK_TAGS
        for metric in fru_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [3173, 6692, 11571, 19529, 30674, 38253, 52063, 54474, 55946, 63960]
    cpu_metrics = ["cpmCPUTotalMonIntervalValue", "cpmCPUMemoryUsed", "cpmCPUMemoryFree"]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common.CHECK_TAGS
        for metric in cpu_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()

def test_dell_poweredge(aggregator):
    instance = common.generate_instance_config([])
    instance['community_string'] = 'dell-poweredge'
    instance['profile'] = 'dell-poweredge'
    instance['enforce_mib_constraints'] = False

    path = os.path.join(os.path.dirname(snmp.__file__), 'data', 'profiles', 'dell-poweredge.yaml')

    init_config = {'profiles': {'dell-poweredge': {'definition_file': path}}}
    check = SnmpCheck('snmp', init_config, [instance])

    
    check.check(instance)

    aggregator.assert_metric('snmp.operatingSystemMemoryAvailablePhysicalSize', metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1)
    aggregator.assert_metric('snmp.operatingSystemMemoryTotalPageFileSize', metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1)
    aggregator.assert_metric('snmp.operatingSystemMemoryAvailablePageFileSize', metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1)
    aggregator.assert_metric('snmp.operatingSystemMemoryTotalVirtualSize', metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1)
    aggregator.assert_metric('snmp.operatingSystemMemoryAvailableVirtualSize', metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1)
    aggregator.assert_metric('snmp.operatingSystemMemoryExtTotalPhysicalSize', metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1) #an octet string (6) but measures kbytes??

    aggregator.assert_metric('snmp.powerSupplyStatus', metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1) 
    aggregator.assert_metric('snmp.powerSupplyOutputWatts', metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1) 
    aggregator.assert_metric('snmp.powerSupplyMaximumInputVoltage', metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1) 
    aggregator.assert_metric('snmp.powerSupplyCurrentInputVoltage', metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1) 



    aggregator.assert_all_metrics_covered()
