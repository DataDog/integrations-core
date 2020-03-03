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
from .utils import mock_profiles_root

pytestmark = pytest.mark.usefixtures("dd_environment")


@pytest.fixture(autouse=True)
def host_profiles_root():
    # By default, we resolve profiles relative to the `snmp.d` directory.
    # But this directory is only created by the Agent when the integration is installed, so we have
    # to replace it with the path within the Python package.
    package_profiles_root = os.path.join(os.path.dirname(snmp.__file__), 'data', 'profiles')

    with mock_profiles_root(package_profiles_root):
        yield


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

    aggregator.all_metrics_asserted()


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
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

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
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

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
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

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
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

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
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

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
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

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
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

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
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

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
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

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
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

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
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

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
    aggregator.assert_all_metrics_covered()


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
        SnmpCheck('snmp', {}, [instance])


def test_discovery(aggregator):
    host = socket.gethostbyname(common.HOST)
    network = ipaddress.ip_network(u'{}/29'.format(host), strict=False).with_prefixlen
    check_tags = ['snmp_device:{}'.format(host), 'snmp_profile:profile1']
    instance = {
        'name': 'snmp_conf',
        # Make sure the check handles bytes
        'network_address': network.encode('utf-8'),
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
        check._thread.join()

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=check_tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance')
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

    aggregator.all_metrics_asserted()


def test_metric_tag_oid(aggregator):
    metrics = common.SUPPORTED_METRIC_TYPES
    instance = common.generate_instance_config(metrics)
    instance['metric_tags'] = [{'OID': '1.3.6.1.2.1.1.5', 'symbol': 'sysName', 'tag': 'snmp_host'}]
    check = common.create_check(instance)

    check.check(instance)

    tags = list(common.CHECK_TAGS)
    tags.append('snmp_host:41ba948911b9')

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=tags, count=1)
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=tags, at_least=1)

    aggregator.all_metrics_asserted()


def test_metric_tag_profile_manual(aggregator):
    instance = common.generate_instance_config([])
    instance['profile'] = 'profile1'
    definition = {
        'metric_tags': [{'OID': '1.3.6.1.2.1.1.5', 'symbol': 'sysName', 'tag': 'snmp_host'}],
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

    aggregator.all_metrics_asserted()


def test_metric_tag_profile_sysoid(aggregator):
    instance = common.generate_instance_config([])
    definition = {
        'metric_tags': [{'OID': '1.3.6.1.2.1.1.5', 'symbol': 'sysName', 'tag': 'snmp_host'}],
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

    aggregator.all_metrics_asserted()


def test_metric_tags_misconfiguration():
    metrics = common.SUPPORTED_METRIC_TYPES
    instance = common.generate_instance_config(metrics)

    instance['metric_tags'] = [{'OID': '1.3.6.1.2.1.1.5', 'tag': 'snmp_host'}]
    with pytest.raises(ConfigurationError):
        common.create_check(instance)

    instance['metric_tags'] = [{'OID': '1.3.6.1.2.1.1.5', 'symbol': 'sysName'}]
    with pytest.raises(ConfigurationError):
        common.create_check(instance)

    instance['metric_tags'] = [{'tag': 'sysName', 'symbol': 'sysName'}]
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


def test_f5(aggregator):
    instance = common.generate_instance_config([])

    instance['community_string'] = 'f5'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'f5-big-ip': {'definition_file': 'f5-big-ip.yaml'}}}
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
    if_counts = [
        'ifHCInOctets',
        'ifInErrors',
        'ifHCOutOctets',
        'ifOutErrors',
        'ifHCInBroadcastPkts',
        'ifHCOutUcastPkts',
        'ifHCOutMulticastPkts',
        'ifOutDiscards',
        'ifHCInUcastPkts',
        'ifHCInMulticastPkts',
        'ifHCOutBroadcastPkts',
        'ifInDiscards',
    ]
    interfaces = ['1.0', 'mgmt', '/Common/internal', '/Common/http-tunnel', '/Common/socks-tunnel']
    tags = ['snmp_profile:f5-big-ip', 'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal']
    tags += common.CHECK_TAGS

    for metric in gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for metric in counts:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)
    for metric in cpu_rates:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=['cpu:0'] + tags, count=1)
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=['cpu:1'] + tags, count=1)
    for metric in if_counts:
        for interface in interfaces:
            aggregator.assert_metric(
                'snmp.{}'.format(metric),
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=['interface:{}'.format(interface)] + tags,
                count=1,
            )
    for metric in if_gauges:
        for interface in interfaces:
            aggregator.assert_metric(
                'snmp.{}'.format(metric),
                metric_type=aggregator.GAUGE,
                tags=['interface:{}'.format(interface)] + tags,
                count=1,
            )
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_router(aggregator):
    instance = common.generate_instance_config([])

    instance['community_string'] = 'network'
    instance['profile'] = 'router'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'router': {'definition_file': 'generic-router.yaml'}}}
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
    common_tags = common.CHECK_TAGS + ['snmp_profile:router']
    for interface in ['eth0', 'eth1']:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for metric in tcp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for metric in tcp_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in udp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common_tags
        for metric in ip_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in ip_if_counts:
            for interface in ['17', '21']:
                tags = ['ipversion:{}'.format(version), 'interface:{}'.format(interface)] + common_tags
                aggregator.assert_metric(
                    'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
                )

    aggregator.assert_all_metrics_covered()


def test_f5_router(aggregator):
    instance = common.generate_instance_config([])

    # Use the generic profile against the f5 device
    instance['community_string'] = 'f5'
    instance['profile'] = 'router'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'router': {'definition_file': 'generic-router.yaml'}}}
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
    common_tags = ['snmp_profile:router', 'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal']
    common_tags.extend(common.CHECK_TAGS)
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common_tags
        for metric in ip_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_3850(aggregator):
    instance = common.generate_instance_config([])

    instance['community_string'] = '3850'
    instance['profile'] = 'cisco-3850'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'cisco-3850': {'definition_file': 'cisco-3850.yaml'}}}
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
    common_tags = common.CHECK_TAGS + ['snmp_host:Cat-3850-4th-Floor.companyname.local', 'snmp_profile:cisco-3850']
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    interfaces = ["Gi1/0/{}".format(i) for i in range(1, 48)]
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in ifx_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
    for metric in tcp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for metric in tcp_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in udp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    sensors = [1006, 1007, 1008, 2006, 2007, 2008]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:8'] + common_tags
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=1)
    fru_metrics = ["cefcFRUPowerAdminStatus", "cefcFRUPowerOperStatus", "cefcFRUCurrent"]
    frus = [1001, 1010, 2001, 2010]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in fru_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [1000, 2000]
    cpu_metrics = ["cpmCPUTotalMonIntervalValue", "cpmCPUMemoryUsed", "cpmCPUMemoryFree"]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in cpu_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    cie_metrics = ["cieIfLastInTime", "cieIfLastOutTime", "cieIfInputQueueDrops", "cieIfOutputQueueDrops"]
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in cie_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_meraki_cloud_controller(aggregator):
    instance = common.generate_instance_config([])

    instance['community_string'] = 'meraki-cloud-controller'
    instance['profile'] = 'meraki'
    instance['enforce_mib_constraints'] = False
    init_config = {'profiles': {'meraki': {'definition_file': 'meraki-cloud-controller.yaml'}}}

    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)

    common_tags = common.CHECK_TAGS + ['snmp_profile:meraki']
    dev_metrics = ['devStatus', 'devClientCount']
    dev_tags = ['device:Gymnasium', 'product:MR16-HW', 'network:L_NETWORK'] + common_tags
    for metric in dev_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=dev_tags, count=1)

    if_tags = ['interface:wifi0', 'index:4'] + common_tags
    if_metrics = ['devInterfaceSentPkts', 'devInterfaceRecvPkts', 'devInterfaceSentBytes', 'devInterfaceRecvBytes']
    for metric in if_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_idrac(aggregator):
    instance = common.generate_instance_config([])

    instance['community_string'] = 'idrac'
    instance['profile'] = 'idrac'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'idrac': {'definition_file': 'idrac.yaml'}}}
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
    common_tags = common.CHECK_TAGS + ['snmp_profile:idrac']
    for interface in interfaces:
        tags = ['adapter:{}'.format(interface)] + common_tags
        for count in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(count), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
    indexes = ['26', '29']
    for index in indexes:
        tags = ['chassis_index:{}'.format(index)] + common_tags
        for gauge in status_gauges:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)
    powers = ['supply1', 'supply2']
    for power in powers:
        tags = ['supply_name:{}'.format(power)] + common_tags
        aggregator.assert_metric('snmp.enclosurePowerSupplyState', metric_type=aggregator.GAUGE, tags=tags, count=1)
    disks = ['disk1', 'disk2']
    for disk in disks:
        tags = ['disk_name:{}'.format(disk)] + common_tags
        for gauge in disk_gauges:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_cisco_nexus(aggregator):
    instance = common.generate_instance_config([])
    instance['community_string'] = 'cisco_nexus'
    instance['profile'] = 'cisco-nexus'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'cisco-nexus': {'definition_file': 'cisco-nexus.yaml'}}}
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

    common_tags = common.CHECK_TAGS + ['snmp_host:Nexus-eu1.companyname.managed', 'snmp_profile:cisco-nexus']

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in ifx_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    for metric in tcp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in tcp_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in udp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    sensors = [1, 9, 11, 12, 12, 14, 17, 26, 29, 31]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:8'] + common_tags
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=1)

    fru_metrics = ["cefcFRUPowerAdminStatus", "cefcFRUPowerOperStatus", "cefcFRUCurrent"]
    frus = [6, 7, 15, 16, 19, 27, 30, 31]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in fru_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [3173, 6692, 11571, 19529, 30674, 38253, 52063, 54474, 55946, 63960]
    cpu_metrics = ["cpmCPUTotalMonIntervalValue", "cpmCPUMemoryUsed", "cpmCPUMemoryFree"]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in cpu_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_dell_poweredge(aggregator):
    instance = common.generate_instance_config([])
    instance['community_string'] = 'dell-poweredge'
    instance['profile'] = 'dell-poweredge'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'dell-poweredge': {'definition_file': 'dell-poweredge.yaml'}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    # Poweredge
    sys_mem_gauges = [
        'operatingSystemMemoryAvailablePhysicalSize',
        'operatingSystemMemoryTotalPageFileSize',
        'operatingSystemMemoryAvailablePageFileSize',
        'operatingSystemMemoryTotalVirtualSize',
        'operatingSystemMemoryAvailableVirtualSize',
    ]
    power_supply_gauges = [
        'powerSupplyStatus',
        'powerSupplyOutputWatts',
        'powerSupplyMaximumInputVoltage',
        'powerSupplyCurrentInputVoltage',
    ]

    temperature_probe_gauges = ['temperatureProbeStatus', 'temperatureProbeReading']

    processor_device_gauges = ['processorDeviceStatus', 'processorDeviceThreadCount']

    cache_device_gauges = ['cacheDeviceStatus', 'cacheDeviceMaximumSize', 'cacheDeviceCurrentSize']

    memory_device_gauges = ['memoryDeviceStatus', 'memoryDeviceFailureModes']

    common_tags = common.CHECK_TAGS + ['snmp_profile:dell-poweredge']

    chassis_indexes = [29, 31]
    for chassis_index in chassis_indexes:
        tags = ['chassis_index:{}'.format(chassis_index)] + common_tags
        for metric in sys_mem_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    indexes = [5, 17]
    for index in indexes:
        tags = ['chassis_index:4', 'index:{}'.format(index)] + common_tags
        for metric in power_supply_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    indexes = [13]
    for index in indexes:
        tags = ['chassis_index:18', 'index:{}'.format(index)] + common_tags
        for metric in temperature_probe_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    indexes = [17, 28]
    for index in indexes:
        tags = ['chassis_index:5', 'index:{}'.format(index)] + common_tags
        for metric in processor_device_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    indexes = [15, 27]
    for index in indexes:
        tags = ['chassis_index:11', 'index:{}'.format(index)] + common_tags
        for metric in cache_device_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    serial_numbers = ['forward zombies acted Jaded', 'kept oxen their their oxen oxen']
    for serial_number in serial_numbers:
        tags = ['serial_number_name:{}'.format(serial_number), 'chassis_index:1'] + common_tags
        for metric in memory_device_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    ip_addresses = ['66.97.1.103', '62.148.76.32', '45.3.243.155']
    for ip_address in ip_addresses:
        tags = ['ip_address:{}'.format(ip_address)] + common_tags
        aggregator.assert_metric('snmp.networkDeviceStatus', metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    # Intel Adapter
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

    interfaces = ['eth0', 'en1']
    for interface in interfaces:
        tags = ['adapter:{}'.format(interface)] + common_tags
        for count in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(count), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    # IDRAC
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

    indexes = ['26', '29']
    for index in indexes:
        tags = ['chassis_index:{}'.format(index)] + common_tags
        for gauge in status_gauges:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)
    powers = ['supply1', 'supply2']
    for power in powers:
        tags = ['supply_name:{}'.format(power)] + common_tags
        aggregator.assert_metric('snmp.enclosurePowerSupplyState', metric_type=aggregator.GAUGE, tags=tags, count=1)
    disks = ['disk1', 'disk2']
    for disk in disks:
        tags = ['disk_name:{}'.format(disk)] + common_tags
        for gauge in disk_gauges:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_hp_ilo4(aggregator):
    instance = common.generate_instance_config([])
    instance['community_string'] = 'hp_ilo4'
    instance['profile'] = 'hp-ilo4'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'hp-ilo4': {'definition_file': 'hp-ilo4.yaml'}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    status_gauges = [
        'cpqHeCritLogCondition',
        'cpqHeCorrMemLogStatus',
        'cpqHeCorrMemLogCondition',
        'cpqHeAsrStatus',
        'cpqHeAsrPost',
        'cpqHeAsrCondition',
        'cpqHeAsrNetworkAccessStatus',
        'cpqHeThermalCondition',
        'cpqHeThermalTempStatus',
        'cpqHeThermalSystemFanStatus',
        'cpqHeThermalCpuFanStatus',
        'cpqNicVtVirusActivity',
        'cpqSm2CntlrServerPowerState',
        'cpqSm2CntlrBatteryStatus',
        'cpqSm2CntlrRemoteSessionStatus',
        'cpqSm2CntlrInterfaceStatus',
    ]

    cpqhlth_counts = ['cpqHeSysUtilLifeTime', 'cpqHeAsrRebootCount', 'cpqHeCorrMemTotalErrs']

    cpqhlth_gauges = ['cpqHeSysUtilEisaBusMin', 'cpqHePowerMeterCurrReading']

    cpqsm2_gauges = [
        'cpqSm2CntlrBatteryPercentCharged',
        'cpqSm2CntlrSelfTestErrors',
        'cpqSm2EventTotalEntries',
    ]

    EMBEDDED = 2
    PCMCIA = 3
    card_locations = [EMBEDDED, PCMCIA]
    network_card_counts = [
        'cpqSm2NicXmitBytes',
        'cpqSm2NicXmitTotalPackets',
        'cpqSm2NicXmitDiscardPackets',
        'cpqSm2NicXmitErrorPackets',
        'cpqSm2NicXmitQueueLength',
        'cpqSm2NicRecvBytes',
        'cpqSm2NicRecvTotalPackets',
        'cpqSm2NicRecvDiscardPackets',
        'cpqSm2NicRecvErrorPackets',
        'cpqSm2NicRecvUnknownPackets',
    ]

    interfaces = ['eth0', 'en1']
    phys_adapter_counts = [
        'cpqNicIfPhysAdapterGoodTransmits',
        'cpqNicIfPhysAdapterGoodReceives',
        'cpqNicIfPhysAdapterBadTransmits',
        'cpqNicIfPhysAdapterBadReceives',
        'cpqNicIfPhysAdapterInOctets',
        'cpqNicIfPhysAdapterOutOctets',
    ]
    phys_adapter_gauges = ['cpqNicIfPhysAdapterSpeed', 'cpqNicIfPhysAdapterSpeedMbps']

    temperature_sensors = [1, 13, 28]
    batteries = [1, 3, 4, 5]

    common_tags = common.CHECK_TAGS + ['snmp_profile:hp-ilo4']

    for metric in status_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in cpqhlth_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in cpqhlth_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in cpqsm2_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for index in temperature_sensors:
        tags = ['temperature_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.cpqHeTemperatureCelsius', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.cpqHeTemperatureCondition', metric_type=aggregator.GAUGE, tags=tags, count=1)

    for index in batteries:
        tags = ['battery_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.cpqHeSysBatteryCondition', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.cpqHeSysBatteryStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    for location in card_locations:
        tags = ['nic_stats_location:{}'.format(location)] + common_tags
        for metric in network_card_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in phys_adapter_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in phys_adapter_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_proliant(aggregator):
    instance = common.generate_instance_config([])
    instance['community_string'] = 'hpe-proliant'
    instance['profile'] = 'hpe-proliant'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'hpe-proliant': {'definition_file': 'hpe-proliant.yaml'}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    common_tags = common.CHECK_TAGS + ['snmp_profile:hpe-proliant']

    cpu_gauges = [
        "cpqSeCpuSlot",
        "cpqSeCpuSpeed",
        "cpqSeCpuStatus",
        "cpqSeCpuExtSpeed",
        "cpqSeCpuCore",
        "cpqSeCPUCoreMaxThreads",
        "cpqSeCpuPrimary",
    ]
    cpu_indexes = [0, 4, 6, 8, 13, 15, 26, 27]
    for idx in cpu_indexes:
        tags = ['cpu_index:{}'.format(idx)] + common_tags
        for metric in cpu_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpu_util_gauges = ["cpqHoCpuUtilMin", "cpqHoCpuUtilFiveMin", "cpqHoCpuUtilThirtyMin", "cpqHoCpuUtilHour"]
    cpu_unit_idx = [4, 7, 13, 20, 22, 23, 29]
    for idx in cpu_unit_idx:
        tags = ['cpu_unit_index:{}'.format(idx)] + common_tags
        for metric in cpu_util_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    file_sys_gauges = [
        "cpqHoFileSysSpaceTotal",
        "cpqHoFileSysSpaceUsed",
        "cpqHoFileSysPercentSpaceUsed",
        "cpqHoFileSysAllocUnitsTotal",
        "cpqHoFileSysAllocUnitsUsed",
        "cpqHoFileSysStatus",
    ]
    file_sys_idx = [5, 8, 11, 15, 19, 21, 28, 30]
    for idx in file_sys_idx:
        tags = ['file_sys_index:{}'.format(idx)] + common_tags
        for metric in file_sys_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    memory_gauges = [
        "cpqSiMemModuleSize",
        "cpqSiMemModuleType",
        "cpqSiMemModuleSpeed",
        "cpqSiMemModuleTechnology",
        "cpqSiMemModuleECCStatus",
        "cpqSiMemModuleFrequency",
        "cpqSiMemModuleCellStatus",
    ]
    memory_idx = [(6, 16), (7, 17), (7, 30), (8, 20), (10, 4), (15, 27), (20, 14), (21, 14), (23, 0), (28, 20)]
    for board_idx, mem_module_index in memory_idx:
        tags = ['mem_board_index:{}'.format(board_idx), "mem_module_index:{}".format(mem_module_index)] + common_tags
        for metric in memory_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    drive_counts = [
        "cpqDaPhyDrvUsedReallocs",
        "cpqDaPhyDrvRefHours",
        "cpqDaPhyDrvHardReadErrs",
        "cpqDaPhyDrvRecvReadErrs",
        "cpqDaPhyDrvHardWriteErrs",
        "cpqDaPhyDrvRecvWriteErrs",
        "cpqDaPhyDrvHSeekErrs",
        "cpqDaPhyDrvSeekErrs",
    ]
    drive_gauges = [
        "cpqDaPhyDrvStatus",
        "cpqDaPhyDrvFactReallocs",
        "cpqDaPhyDrvSpinupTime",
        "cpqDaPhyDrvSize",
        "cpqDaPhyDrvSmartStatus",
        "cpqDaPhyDrvCurrentTemperature",
    ]
    drive_idx = [(0, 2), (0, 28), (8, 31), (9, 24), (9, 28), (10, 17), (11, 4), (12, 20), (18, 22), (23, 2)]
    for drive_cntrl_idx, drive_index in drive_idx:
        tags = ['drive_cntrl_idx:{}'.format(drive_cntrl_idx), "drive_index:{}".format(drive_index)] + common_tags
        for metric in drive_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in drive_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_generic_host_resources(aggregator):
    instance = common.generate_instance_config([])

    instance['community_string'] = 'generic_host'
    instance['profile'] = 'generic'
    instance['enforce_mib_constraints'] = False

    # We need the full path as we're not in installed mode
    path = os.path.join(os.path.dirname(snmp.__file__), 'data', 'profiles', '_generic-host-resources.yaml')
    init_config = {'profiles': {'generic': {'definition_file': path}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    common_tags = common.CHECK_TAGS + ['snmp_profile:generic']

    sys_metrics = [
        'snmp.hrSystemUptime',
        'snmp.hrSystemNumUsers',
        'snmp.hrSystemProcesses',
        'snmp.hrSystemMaxProcesses',
    ]
    for metric in sys_metrics:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    aggregator.assert_metric('snmp.hrStorageAllocationUnits', count=2)
    aggregator.assert_metric('snmp.hrStorageSize', count=2)
    aggregator.assert_metric('snmp.hrStorageUsed', count=2)
    aggregator.assert_metric('snmp.hrStorageAllocationFailures', count=2)

    aggregator.assert_metric('snmp.hrProcessorLoad', count=2)

    aggregator.assert_all_metrics_covered()


def test_palo_alto(aggregator):
    instance = common.generate_instance_config([])

    instance['community_string'] = 'pan-common'
    instance['profile'] = 'palo-alto'
    instance['enforce_mib_constraints'] = False

    # We need the full path as we're not in installed mode
    path = os.path.join(os.path.dirname(snmp.__file__), 'data', 'profiles', 'palo-alto.yaml')
    init_config = {'profiles': {'palo-alto': {'definition_file': path}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)

    common_tags = common.CHECK_TAGS + ['snmp_profile:palo-alto']

    session = [
        'panSessionUtilization',
        'panSessionMax',
        'panSessionActive',
        'panSessionActiveTcp',
        'panSessionActiveUdp',
        'panSessionActiveICMP',
        'panSessionActiveSslProxy',
        'panSessionSslProxyUtilization',
    ]

    global_protect = [
        'panGPGWUtilizationPct',
        'panGPGWUtilizationMaxTunnels',
        'panGPGWUtilizationActiveTunnels',
    ]

    for metric in session:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in global_protect:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    aggregator.assert_all_metrics_covered()
def test_cisco_asa_5525(aggregator):
    instance = common.generate_instance_config([])
    instance['community_string'] = 'cisco_asa_5525'
    instance['profile'] = 'cisco-asa-5525'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'cisco-asa-5525': {'definition_file': 'cisco-asa-5525.yaml'}}}
    check = SnmpCheck('snmp', init_config, [instance])

    check.check(instance)
    
    common_tags = common.CHECK_TAGS + ['snmp_profile:cisco-asa-5525', 'snmp_host:kept']

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

    for metric in tcp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in tcp_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in udp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    fru_metrics = ["cefcFRUPowerAdminStatus", "cefcFRUPowerOperStatus", "cefcFRUCurrent"]
    frus = [3, 4, 5, 7, 16, 17, 24, 25]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in fru_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
