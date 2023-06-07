# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from .. import common


def create_profile_test_config(profile_name):
    config = common.generate_container_instance_config([])
    config['init_config']['loader'] = 'core'
    instance = config['instances'][0]
    instance.update({'community_string': profile_name})
    return config


def get_device_ip_from_config(config):
    return config['instances'][0]['ip_address']
