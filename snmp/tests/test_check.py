# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import mock
import pytest
import yaml

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
    mib_folders = config.snmp_engine.getMibBuilder().getMibSources()
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
    When failing with 'snmpget' command, SNMP check falls back to 'snpgetnext'

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

    assert "failed at: ValueConstraintError" in check._error

    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.CRITICAL, tags=common.CHECK_TAGS, at_least=1)


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
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.CRITICAL, tags=common.CHECK_TAGS, at_least=1)


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
    with temp_dir() as tmp:
        profile_file = os.path.join(tmp, 'profile1.yaml')
        with open(profile_file, 'w') as f:
            f.write(yaml.safe_dump(common.SUPPORTED_METRIC_TYPES))
        init_config = {'profiles': {'profile1': {'definition': profile_file}}}
        check = SnmpCheck('snmp', init_config, [instance])
        check.check(instance)

    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=1)
    aggregator.assert_all_metrics_covered()
