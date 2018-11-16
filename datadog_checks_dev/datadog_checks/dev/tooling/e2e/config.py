# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import yaml

from ..config import APP_DIR
from ...utils import file_exists, ensure_dir_exists, dir_exists, path_join, read_file, remove_path, write_file

ENV_DIR = path_join(APP_DIR, 'envs')


def config_file_name(check):
    return '{}.yaml'.format(check)


def locate_env_dir(check, env):
    return path_join(ENV_DIR, check, env)


def locate_config_dir(check, env):
    return path_join(locate_env_dir(check, env), 'config')


def locate_config_file(check, env):
    return path_join(locate_config_dir(check, env), config_file_name(check))


def locate_metadata_file(check, env):
    return path_join(locate_env_dir(check, env), 'metadata.json')


def env_exists(check, env):
    return dir_exists(locate_env_dir(check, env))


def get_configured_envs(check):
    envs = []

    env_dir = path_join(ENV_DIR, check)
    if dir_exists(env_dir):
        envs[:] = os.listdir(env_dir)
        envs.sort()

    return envs


def get_configured_checks():
    envs = []

    root_dir = path_join(ENV_DIR)
    if dir_exists(root_dir):
        envs[:] = os.listdir(root_dir)
        envs.sort()

    return envs


def remove_env_root(check):
    remove_path(path_join(ENV_DIR, check))


def remove_env_data(check, env):
    remove_path(locate_env_dir(check, env))


def read_env_data(check, env):
    config_file = locate_config_file(check, env)
    if file_exists(config_file):
        config = yaml.load(read_file(config_file))
    else:
        config = {}

    metadata_file = locate_metadata_file(check, env)
    if file_exists(metadata_file):
        metadata = json.loads(read_file(metadata_file))
    else:
        metadata = {}

    return config, metadata


def write_env_data(check, env, config=None, metadata=None):
    ensure_dir_exists(locate_config_dir(check, env))

    if config:
        write_file(locate_config_file(check, env), config_to_yaml(config))

    if metadata:
        write_file(locate_metadata_file(check, env), metadata_to_json(metadata))


def config_to_yaml(config):
    if 'instances' not in config:
        config = {'instances': [config]}

    # Agent 5 requires init_config
    if 'init_config' not in config:
        _config = {'init_config': {}}
        _config.update(config)
        config = _config

    return yaml.safe_dump(config, default_flow_style=False)


def metadata_to_json(metadata):
    return json.dumps(metadata, indent=2, separators=(',', ': '))
