# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from time import time as timestamp

import requests

from datadog_checks.checks import AgentCheck
from datadog_checks.config import _is_affirmative
from datadog_checks.utils.containers import hash_mutable
from .errors import ApiUnreachable


class Vault(AgentCheck):
    CHECK_NAME = 'vault'
    DEFAULT_API_VERSION = '1'
    EVENT_LEADER_CHANGE = 'vault.leader_change'
    SERVICE_CHECK_CONNECT = 'vault.can_connect'
    SERVICE_CHECK_UNSEALED = 'vault.unsealed'
    SERVICE_CHECK_INITIALIZED = 'vault.initialized'

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(Vault, self).__init__(name, init_config, agentConfig, instances)
        self.api_versions = {
            '1': {
                'functions': {
                    'check_leader': self.check_leader_v1,
                    'check_health': self.check_health_v1,
                }
            },
        }
        self.config = {}

    def check(self, instance):
        config = self.get_config(instance)
        if config is None:
            return

        tags = list(config['tags'])

        try:
            config['api']['check_leader'](config, tags)
            config['api']['check_health'](config, tags)
        except ApiUnreachable:
            return

        self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.OK, tags=tags)

    def check_leader_v1(self, config, tags):
        url = config['api_url'] + '/sys/leader'
        leader_data = self.access_api(url, config, tags).json()

        is_leader = _is_affirmative(leader_data.get('is_self'))
        tags.append('is_leader:{}'.format('true' if is_leader else 'false'))

        current_leader = leader_data.get('leader_address')
        previous_leader = config['leader']
        if config['detect_leader'] and current_leader:
            if previous_leader is not None and current_leader != previous_leader:
                self.event({
                    'timestamp': timestamp(),
                    'event_type': self.EVENT_LEADER_CHANGE,
                    'msg_title': 'Leader change',
                    'msg_text': 'Leader changed from `{}` to `{}`.'.format(previous_leader, current_leader),
                    'alert_type': 'info',
                    'source_type_name': self.CHECK_NAME,
                    'host': self.hostname,
                    'tags': tags,
                })
            config['leader'] = current_leader

    def check_health_v1(self, config, tags):
        url = config['api_url'] + '/sys/health'
        health_data = self.access_api(url, config, tags).json()

        cluster_name = health_data.get('cluster_name')
        if cluster_name:
            tags.append('cluster_name:{}'.format(cluster_name))

        vault_version = health_data.get('version')
        if vault_version:
            tags.append('vault_version:{}'.format(vault_version))

        unsealed = not _is_affirmative(health_data.get('sealed'))
        if unsealed:
            self.service_check(self.SERVICE_CHECK_UNSEALED, AgentCheck.OK, tags=tags)
        else:
            self.service_check(self.SERVICE_CHECK_UNSEALED, AgentCheck.CRITICAL, tags=tags)

        initialized = _is_affirmative(health_data.get('initialized'))
        if initialized:
            self.service_check(self.SERVICE_CHECK_INITIALIZED, AgentCheck.OK, tags=tags)
        else:
            self.service_check(self.SERVICE_CHECK_INITIALIZED, AgentCheck.CRITICAL, tags=tags)

    def get_config(self, instance):
        instance_id = hash_mutable(instance)
        config = self.config.get(instance_id)
        if config is None:
            config = {}

            try:
                api_url = instance['api_url']
                api_version = api_url[-1]
                if api_version not in self.api_versions:
                    self.log.warning(
                        'Unknown Vault API version `{}`, using version '
                        '`{}`'.format(api_version, self.DEFAULT_API_VERSION)
                    )

                config['api_url'] = api_url
                config['api'] = self.api_versions.get(api_version, self.DEFAULT_API_VERSION)['functions']
            except KeyError:
                self.log.error('Vault configuration setting `api_url` is required')
                return

            client_token = instance.get('client_token')
            config['headers'] = {'X-Vault-Token': client_token} if client_token else None

            username = instance.get('username')
            password = instance.get('password')
            config['auth'] = (username, password) if username and password else None

            config['ssl_verify'] = _is_affirmative(instance.get('ssl_verify', True))
            config['proxies'] = self.get_instance_proxy(instance, config['api_url'])
            config['timeout'] = int(instance.get('timeout', 20))
            config['tags'] = instance.get('tags', [])

            # Keep track of the previous cluster leader to detect changes.
            config['leader'] = None
            config['detect_leader'] = _is_affirmative(instance.get('detect_leader'))

            self.config[instance_id] = config

        return config

    def access_api(self, url, config, tags):
        try:
            response = requests.get(
                url,
                auth=config['auth'],
                verify=config['ssl_verify'],
                proxies=config['proxies'],
                timeout=config['timeout'],
                headers=config['headers']
            )
        except requests.exceptions.Timeout:
            msg = 'Vault endpoint `{}` timed out after {} seconds'.format(url, config['timeout'])
            self.service_check(
                self.SERVICE_CHECK_CONNECT,
                AgentCheck.CRITICAL,
                message=msg,
                tags=tags
            )
            self.log.exception(msg)
            raise ApiUnreachable
        except (requests.exceptions.RequestException, requests.exceptions.ConnectionError):
            msg = 'Error accessing Vault endpoint `{}`'.format(url)
            self.service_check(
                self.SERVICE_CHECK_CONNECT,
                AgentCheck.CRITICAL,
                message=msg,
                tags=tags
            )
            self.log.exception(msg)
            raise ApiUnreachable

        return response
