# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .. import common


def create_e2e_core_test_config(community_string):
    """
    The community_string must correspond to a .snmprec file name.
    It is used to tell snmpsim to use the corresponding .snmprec file.
    """
    config = common.generate_container_instance_config([])
    config['init_config']['loader'] = 'core'
    instance = config['instances'][0]
    instance.update({'community_string': community_string})
    return config


def get_device_ip_from_config(config):
    return config['instances'][0]['ip_address']


def assert_common_metrics(aggregator, common_tags):
    common.assert_common_metrics(aggregator, tags=common_tags, is_e2e=True, loader='core')


def assert_extend_generic_if(aggregator, common_tags):
    aggregator.assert_metric('snmp.ifNumber', metric_type=aggregator.GAUGE, tags=common_tags)
