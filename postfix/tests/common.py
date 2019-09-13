# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import getpass

from datadog_checks.dev._env import deserialize_data, get_env_vars


def get_data_dir():
    return deserialize_data(get_env_vars().get('data_dir'))


def get_queues():
    return deserialize_data(get_env_vars().get('postfix_queues'))


def get_queue_counts():
    return deserialize_data(get_env_vars().get('queue_counts'))


def get_instance():
    return {'directory': get_data_dir(), 'queues': get_queues(), 'postfix_user': getpass.getuser()}


def get_e2e_instance():
    return {'directory': '/home/postfix_data', 'queues': get_queues(), 'postfix_user': 'dd-agent'}


def get_e2e_metadata():
    return {'docker_volumes': ['{}:/home/postfix_data'.format(get_data_dir())]}
