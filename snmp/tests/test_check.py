# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from . import common

from datadog_checks.snmp import SnmpCheck


def test_command_generator(aggregator):
    """
    Command generator's parameters should match init_config
    """
    check = SnmpCheck('snmp', common.MIBS_FOLDER, {}, {})
    cmdgen, _, _, _, _, _, _ = check._load_conf(common.SNMP_CONF)

    # Test command generator MIB source
    mib_folders = cmdgen.snmpEngine.msgAndPduDsp\
        .mibInstrumController.mibBuilder.getMibSources()
    full_path_mib_folders = map(lambda f: f.fullPath(), mib_folders)

    assert "/etc/mibs" in full_path_mib_folders
    assert not cmdgen.ignoreNonIncreasingOid

    # Test command generator `ignoreNonIncreasingOid` parameter
    check = SnmpCheck('snmp', common.IGNORE_NONINCREASING_OID, {}, {})
    cmdgen, _, _, _, _, _, _ = check._load_conf(common.SNMP_CONF)
    assert cmdgen.ignoreNonIncreasingOid


def test_type_support(spin_up_snmp, aggregator, check):
    """
    Support expected types
    """
    metrics = common.SUPPORTED_METRIC_TYPES + common.UNSUPPORTED_METRICS
    instance = common.generate_instance_config(metrics)

    check.check(instance)

    common.wait_for_async(check, aggregator)

    # Test metrics
    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=1)
    for metric in common.UNSUPPORTED_METRICS:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=0)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK,
                                    tags=common.CHECK_TAGS, at_least=1)

    aggregator.all_metrics_asserted()


def test_snmpget(spin_up_snmp, aggregator, check):
    """
    When failing with 'snmpget' command, SNMP check falls back to 'snpgetnext'

        > snmpget -v2c -c public localhost:11111 1.3.6.1.2.1.25.6.3.1.4
        iso.3.6.1.2.1.25.6.3.1.4 = No Such Instance currently exists at this OID
        > snmpgetnext -v2c -c public localhost:11111 1.3.6.1.2.1.25.6.3.1.4
        iso.3.6.1.2.1.25.6.3.1.4.0 = INTEGER: 4
    """
    instance = common.generate_instance_config(common.PLAY_WITH_GET_NEXT_METRICS)

    check.check(instance)

    common.wait_for_async(check, aggregator)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK,
                                    tags=common.CHECK_TAGS, at_least=1)

    check.check(instance)
    common.wait_for_async(check, aggregator)

    # Test metrics
    for metric in common.PLAY_WITH_GET_NEXT_METRICS:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, at_least=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK,
                                    tags=common.CHECK_TAGS, at_least=1)

    aggregator.all_metrics_asserted()


def test_scalar(spin_up_snmp, aggregator, check):
    """
    Support SNMP scalar objects
    """
    instance = common.generate_instance_config(common.SCALAR_OBJECTS)

    check.check(instance)
    common.wait_for_async(check, aggregator)

    # Test metrics
    for metric in common.SCALAR_OBJECTS:
        metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS, count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check",
                                    status=SnmpCheck.OK,
                                    tags=common.CHECK_TAGS,
                                    at_least=1)

    aggregator.all_metrics_asserted()


def test_table(spin_up_snmp, aggregator, check):
    """
    Support SNMP tabular objects
    """
    instance = common.generate_instance_config(common.TABULAR_OBJECTS)

    check.check(instance)
    common.wait_for_async(check, aggregator)

    # Test metrics
    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check",
                                    status=SnmpCheck.OK,
                                    tags=common.CHECK_TAGS,
                                    at_least=1)

    aggregator.all_metrics_asserted()


def test_table_v3_MD5_DES(spin_up_snmp, aggregator, check):
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
        priv_key=common.PRIV_KEY
    )

    check.check(instance)
    common.wait_for_async(check, aggregator)

    # Test metrics
    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check",
                                    status=SnmpCheck.OK,
                                    tags=common.CHECK_TAGS,
                                    at_least=1)

    aggregator.all_metrics_asserted()


def test_table_v3_MD5_AES(spin_up_snmp, aggregator, check):
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
        priv_key=common.PRIV_KEY
    )

    check.check(instance)
    common.wait_for_async(check, aggregator)

    # Test metrics
    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check",
                                    status=SnmpCheck.OK,
                                    tags=common.CHECK_TAGS,
                                    at_least=1)

    aggregator.all_metrics_asserted()


def test_table_v3_SHA_DES(spin_up_snmp, aggregator, check):
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
        priv_key=common.PRIV_KEY
    )

    check.check(instance)
    common.wait_for_async(check, aggregator)

    # Test metrics
    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check",
                                    status=SnmpCheck.OK,
                                    tags=common.CHECK_TAGS,
                                    at_least=1)

    aggregator.all_metrics_asserted()


def test_table_v3_SHA_AES(spin_up_snmp, aggregator, check):
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
        priv_key=common.PRIV_KEY
    )

    check.check(instance)
    common.wait_for_async(check, aggregator)

    # Test metrics
    for symbol in common.TABULAR_OBJECTS[0]['symbols']:
        metric_name = "snmp." + symbol
        aggregator.assert_metric(metric_name, at_least=1)
        aggregator.assert_metric_has_tag(metric_name, common.CHECK_TAGS[0], at_least=1)

        for mtag in common.TABULAR_OBJECTS[0]['metric_tags']:
            tag = mtag['tag']
            aggregator.assert_metric_has_tag_prefix(metric_name, tag, at_least=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check",
                                    status=SnmpCheck.OK,
                                    tags=common.CHECK_TAGS,
                                    at_least=1)

    aggregator.all_metrics_asserted()


def test_invalid_metric(spin_up_snmp, aggregator, check):
    """
    Invalid metrics raise a Warning and a critical service check
    """

    instance = common.generate_instance_config(common.INVALID_METRICS)
    check.check(instance)

    common.wait_for_async(check, aggregator)

    # Test service check
    aggregator.assert_service_check("snmp.can_check",
                                    status=SnmpCheck.CRITICAL,
                                    tags=common.CHECK_TAGS,
                                    at_least=1)


def test_forcedtype_metric(spin_up_snmp, aggregator, check):
    """
    Forced Types should be reported as metrics of the forced type
    """
    instance = common.generate_instance_config(common.FORCED_METRICS)
    check.check(instance)
    common.wait_for_async(check, aggregator)

    for metric in common.FORCED_METRICS:
        metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
        if metric.get('forced_type') == 'counter':
            # rate will be flushed as a gauge, so count should be 0.
            aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS,
                                     count=0, metric_type=aggregator.GAUGE)
        elif metric.get('forced_type') == 'gauge':
            aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS,
                                     at_least=1, metric_type=aggregator.GAUGE)

    # Test service check
    aggregator.assert_service_check("snmp.can_check",
                                    status=SnmpCheck.OK,
                                    tags=common.CHECK_TAGS,
                                    at_least=1)

    aggregator.all_metrics_asserted()


def test_invalid_forcedtype_metric(spin_up_snmp, aggregator, check):
    """
    If a forced type is invalid a warning should be issued + a service check
    should be available
    """
    instance = common.generate_instance_config(common.INVALID_FORCED_METRICS)

    check.check(instance)
    common.wait_for_async(check, aggregator)

    # Test service check
    aggregator.assert_service_check("snmp.can_check",
                                    status=SnmpCheck.CRITICAL,
                                    tags=common.CHECK_TAGS,
                                    at_least=1)


def test_scalar_with_tags(spin_up_snmp, aggregator, check):
    """
    Support SNMP scalar objects with tags
    """
    instance = common.generate_instance_config(common.SCALAR_OBJECTS_WITH_TAGS)

    check.check(instance)
    common.wait_for_async(check, aggregator)

    # Test metrics
    for metric in common.SCALAR_OBJECTS_WITH_TAGS:
        metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
        tags = common.CHECK_TAGS + metric.get('metric_tags')
        aggregator.assert_metric(metric_name, tags=tags, count=1)

    # Test service check
    aggregator.assert_service_check("snmp.can_check",
                                    status=SnmpCheck.OK,
                                    tags=common.CHECK_TAGS,
                                    at_least=1)

    aggregator.all_metrics_asserted()


def test_network_failure(spin_up_snmp, aggregator, check):
    """
    Network failure is reported in service check
    """
    instance = common.generate_instance_config(common.SCALAR_OBJECTS)

    # Change port so connection will fail
    instance['port'] = 162

    check.check(instance)

    # Test service check
    aggregator.assert_service_check("snmp.can_check",
                                    status=SnmpCheck.CRITICAL,
                                    tags=common.CHECK_TAGS,
                                    at_least=1)

    aggregator.all_metrics_asserted()
