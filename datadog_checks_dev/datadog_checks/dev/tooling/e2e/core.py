# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .config import read_env_data
from .docker import DockerInterface


def derive_interface(env_type):
    if env_type == 'docker':
        return DockerInterface


def create_interface(check, env):
    possible_config, possible_metadata = read_env_data(check, env)
    possible_metadata.setdefault('env_type', 'docker')
    interface = derive_interface(possible_metadata['env_type'])

    return interface(check, env, config=possible_config, metadata=possible_metadata)
