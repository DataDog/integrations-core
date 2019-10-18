# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from time import time as timestamp

import requests
from simplejson import JSONDecodeError

from datadog_checks.checks import AgentCheck
from datadog_checks.config import is_affirmative
from datadog_checks.utils.containers import hash_mutable

from .errors import ApiUnreachable


class Vault(AgentCheck):
    CHECK_NAME = 'vault'
    DEFAULT_API_VERSION = '1'
    EVENT_LEADER_CHANGE = 'vault.leader_change'
    SERVICE_CHECK_CONNECT = 'vault.can_connect'
    SERVICE_CHECK_UNSEALED = 'vault.unsealed'
    SERVICE_CHECK_INITIALIZED = 'vault.initialized'

    HTTP_CONFIG_REMAPPER = {
        'ssl_verify': {'name': 'tls_verify'},
        'ssl_cert': {'name': 'tls_cert'},
        'ssl_private_key': {'name': 'tls_private_key'},
        'ssl_ca_cert': {'name': 'tls_ca_cert'},
        'ssl_ignore_warning': {'name': 'tls_ignore_warning'},
    }

    def __init__(self, name, init_config, instances):
        super(Vault, self).__init__(name, init_config, instances)
        self.api_versions = {
            '1': {'functions': {'check_leader': self.check_leader_v1, 'check_health': self.check_health_v1}}
        }
        self.config = {}
        if 'client_token' in self.instance:
            self.http.options['headers']['X-Vault-Token'] = self.instance['client_token']

    def check(self, instance):
        config = self.get_config(instance)
        if config is None:
            return

        api = config['api']
        tags = list(config['tags'])

        # We access the version of the Vault API corresponding to each instance's `api_url`.
        try:
            api['check_leader'](config, tags)
            api['check_health'](config, tags)
        except ApiUnreachable:
            raise

        self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.OK, tags=tags)

    def check_leader_v1(self, config, tags):
        url = config['api_url'] + '/sys/leader'
        leader_data = self.access_api(url, tags)

        is_leader = is_affirmative(leader_data.get('is_self'))
        tags.append('is_leader:{}'.format('true' if is_leader else 'false'))

        self.gauge('vault.is_leader', int(is_leader), tags=tags)

        current_leader = leader_data.get('leader_address')
        previous_leader = config['leader']
        if config['detect_leader'] and current_leader:
            if previous_leader is not None and current_leader != previous_leader:
                self.event(
                    {
                        'timestamp': timestamp(),
                        'event_type': self.EVENT_LEADER_CHANGE,
                        'msg_title': 'Leader change',
                        'msg_text': 'Leader changed from `{}` to `{}`.'.format(previous_leader, current_leader),
                        'alert_type': 'info',
                        'source_type_name': self.CHECK_NAME,
                        'host': self.hostname,
                        'tags': tags,
                    }
                )
            config['leader'] = current_leader

    def check_health_v1(self, config, tags):
        url = config['api_url'] + '/sys/health'
        health_params = {'standbyok': True, 'perfstandbyok': True}
        health_data = self.access_api(url, tags, params=health_params)

        cluster_name = health_data.get('cluster_name')
        if cluster_name:
            tags.append('cluster_name:{}'.format(cluster_name))

        vault_version = health_data.get('version')
        if vault_version:
            tags.append('vault_version:{}'.format(vault_version))

        unsealed = not is_affirmative(health_data.get('sealed'))
        if unsealed:
            self.service_check(self.SERVICE_CHECK_UNSEALED, AgentCheck.OK, tags=tags)
        else:
            self.service_check(self.SERVICE_CHECK_UNSEALED, AgentCheck.CRITICAL, tags=tags)

        initialized = is_affirmative(health_data.get('initialized'))
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
                    api_url = api_url[:-1] + self.DEFAULT_API_VERSION
                    api_version = self.DEFAULT_API_VERSION

                config['api_url'] = api_url
                config['api'] = self.api_versions[api_version]['functions']
            except KeyError:
                self.log.error('Vault configuration setting `api_url` is required')
                return

            config['tags'] = instance.get('tags', [])

            # Keep track of the previous cluster leader to detect changes.
            config['leader'] = None
            config['detect_leader'] = is_affirmative(instance.get('detect_leader'))

            self.config[instance_id] = config

        return config

    def access_api(self, url, tags, params=None):
        try:
            response = self.http.get(url, params=params)
            response.raise_for_status()
            json_data = response.json()
        except requests.exceptions.HTTPError:
            msg = 'The Vault endpoint `{}` returned {}.'.format(url, response.status_code)
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.CRITICAL, message=msg, tags=tags)
            self.log.exception(msg)
            raise ApiUnreachable
        except JSONDecodeError:
            msg = 'The Vault endpoint `{}` returned invalid json data.'.format(url)
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.CRITICAL, message=msg, tags=tags)
            self.log.exception(msg)
            raise ApiUnreachable
        except requests.exceptions.Timeout:
            msg = 'Vault endpoint `{}` timed out after {} seconds'.format(url, self.http.options['timeout'])
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.CRITICAL, message=msg, tags=tags)
            self.log.exception(msg)
            raise ApiUnreachable
        except (requests.exceptions.RequestException, requests.exceptions.ConnectionError):
            msg = 'Error accessing Vault endpoint `{}`'.format(url)
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.CRITICAL, message=msg, tags=tags)
            self.log.exception(msg)
            raise ApiUnreachable

        return json_data
