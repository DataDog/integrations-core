# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests
from six import iteritems, string_types
from six.moves.urllib.parse import urlparse

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck, is_affirmative
from datadog_checks.base.utils.headers import headers
from .metrics import METRIC_MAP


class Etcd(OpenMetricsBaseCheck):

    DEFAULT_TIMEOUT = 5

    SERVICE_CHECK_NAME = 'etcd.can_connect'
    HEALTH_SERVICE_CHECK_NAME = 'etcd.healthy'
    HEALTH_KEY = 'health'

    STORE_RATES = {
        'getsSuccess': 'etcd.store.gets.success',
        'getsFail': 'etcd.store.gets.fail',
        'setsSuccess': 'etcd.store.sets.success',
        'setsFail': 'etcd.store.sets.fail',
        'deleteSuccess': 'etcd.store.delete.success',
        'deleteFail': 'etcd.store.delete.fail',
        'updateSuccess': 'etcd.store.update.success',
        'updateFail': 'etcd.store.update.fail',
        'createSuccess': 'etcd.store.create.success',
        'createFail': 'etcd.store.create.fail',
        'compareAndSwapSuccess': 'etcd.store.compareandswap.success',
        'compareAndSwapFail': 'etcd.store.compareandswap.fail',
        'compareAndDeleteSuccess': 'etcd.store.compareanddelete.success',
        'compareAndDeleteFail': 'etcd.store.compareanddelete.fail',
        'expireCount': 'etcd.store.expire.count'
    }

    STORE_GAUGES = {
        'watchers': 'etcd.store.watchers'
    }

    LEADER_GAUGES = {
        'sendPkgRate': 'etcd.self.send.pkgrate',
        'sendBandwidthRate': 'etcd.self.send.bandwidthrate'
    }

    FOLLOWER_GAUGES = {
        'recvPkgRate': 'etcd.self.recv.pkgrate',
        'recvBandwidthRate': 'etcd.self.recv.bandwidthrate'
    }

    SELF_RATES = {
        'recvAppendRequestCnt': 'etcd.self.recv.appendrequest.count',
        'sendAppendRequestCnt': 'etcd.self.send.appendrequest.count'
    }

    LEADER_COUNTS = {
        # Rates
        'fail': 'etcd.leader.counts.fail',
        'success': 'etcd.leader.counts.success',
    }

    LEADER_LATENCY = {
        # Gauges
        'current': 'etcd.leader.latency.current',
        'average': 'etcd.leader.latency.avg',
        'minimum': 'etcd.leader.latency.min',
        'maximum': 'etcd.leader.latency.max',
        'standardDeviation': 'etcd.leader.latency.stddev',
    }

    def __init__(self, name, init_config, agentConfig, instances=None):
        if instances is not None:
            for instance in instances:
                # For legacy check ensure prometheus_url is set so
                # OpenMetricsBaseCheck instantiation succeeds
                if not is_affirmative(instance.get('use_preview', False)):
                    instance.setdefault('prometheus_url', '')

        super(Etcd, self).__init__(
            name,
            init_config,
            agentConfig,
            instances,
            default_instances={
                'etcd': {
                    'prometheus_url': 'http://localhost:2379/metrics',
                    'namespace': 'etcd',
                    'metrics': [METRIC_MAP],
                    'send_histograms_buckets': True,
                }
            },
            default_namespace='etcd',
        )

    def check(self, instance):
        if is_affirmative(instance.get('use_preview', False)):
            self.check_post_v3(instance)
        else:
            self.warning(
                'In Agent 6.10 this check will only support ETCD v3+. If you '
                'wish to preview the new version, set `use_preview` to `true`.'
            )
            self.check_pre_v3(instance)

    def access_api(self, scraper_config, path, data='{}'):
        url = urlparse(scraper_config['prometheus_url'])
        endpoint = '{}://{}{}'.format(url.scheme, url.netloc, path)

        timeout = scraper_config['prometheus_timeout']

        username = scraper_config['username']
        password = scraper_config['password']
        auth = (username, password) if username and password else None

        cert = None
        if isinstance(scraper_config['ssl_cert'], string_types):
            if isinstance(scraper_config['ssl_private_key'], string_types):
                cert = (scraper_config['ssl_cert'], scraper_config['ssl_private_key'])
            else:
                cert = scraper_config['ssl_cert']

        verify = True
        if isinstance(scraper_config['ssl_ca_cert'], string_types):
            verify = scraper_config['ssl_ca_cert']
        elif not is_affirmative(scraper_config['ssl_verify']):
            verify = False

        response = {}
        try:
            r = requests.post(endpoint, data=data, timeout=timeout, auth=auth, verify=verify, cert=cert)
            response.update(r.json())
        except Exception as e:
            self.log.debug('Error accessing GRPC gateway: {}'.format(e))

        return response

    def is_leader(self, scraper_config):
        # Modify endpoint as etcd stabilizes
        # https://github.com/etcd-io/etcd/blob/master/Documentation/dev-guide/api_grpc_gateway.md#notes
        response = self.access_api(scraper_config, '/v3beta/maintenance/status')

        leader = response.get('leader')
        member = response.get('header', {}).get('member_id')

        return leader and member and leader == member

    def add_leader_state_tag(self, scraper_config, tags):
        is_leader = self.is_leader(scraper_config)

        if is_leader is not None:
            tags.append('is_leader:{}'.format('true' if is_leader else 'false'))

    def check_post_v3(self, instance):
        scraper_config = self.get_scraper_config(instance)

        if 'prometheus_url' not in scraper_config:
            raise ConfigurationError(
                'You have to define at least one `prometheus_url`.'
            )

        if not scraper_config.get('metrics_mapper'):
            raise ConfigurationError(
                'You have to collect at least one metric from the endpoint `{}`.'.format(
                    scraper_config['prometheus_url']
                )
            )

        tags = []
        self.add_leader_state_tag(scraper_config, tags)

        scraper_config['_metric_tags'][:] = tags

        self.process(scraper_config)

    def check_pre_v3(self, instance):
        if 'url' not in instance:
            raise Exception('etcd instance missing "url" value.')

        # Load values from the instance config
        url = instance['url']
        instance_tags = instance.get('tags', [])

        # Load the ssl configuration
        ssl_params = {
            'ssl_keyfile': instance.get('ssl_keyfile'),
            'ssl_certfile': instance.get('ssl_certfile'),
            'ssl_cert_validation': is_affirmative(instance.get('ssl_cert_validation', True)),
            'ssl_ca_certs': instance.get('ssl_ca_certs'),
        }

        for key, param in list(iteritems(ssl_params)):
            if param is None:
                del ssl_params[key]

        # Get a copy of tags for the CRIT statuses
        critical_tags = list(instance_tags)

        # Append the instance's URL in case there are more than one, that
        # way they can tell the difference!
        instance_tags.append('url:{}'.format(url))
        timeout = float(instance.get('timeout', self.DEFAULT_TIMEOUT))
        is_leader = False

        # Gather self health status
        sc_state = self.UNKNOWN
        health_status = self._get_health_status(url, ssl_params, timeout)
        if health_status is not None:
            sc_state = self.OK if self._is_healthy(health_status) else self.CRITICAL
        self.service_check(self.HEALTH_SERVICE_CHECK_NAME, sc_state, tags=instance_tags)

        # Gather self metrics
        self_response = self._get_self_metrics(url, ssl_params, timeout, critical_tags)
        if self_response is not None:
            if self_response['state'] == 'StateLeader':
                is_leader = True
                instance_tags.append('etcd_state:leader')
                gauges = self.LEADER_GAUGES
            else:
                instance_tags.append('etcd_state:follower')
                gauges = self.FOLLOWER_GAUGES

            for key in self.SELF_RATES:
                if key in self_response:
                    self.rate(self.SELF_RATES[key], self_response[key], tags=instance_tags)
                else:
                    self.log.warn('Missing key {} in stats.'.format(key))

            for key in gauges:
                if key in self_response:
                    self.gauge(gauges[key], self_response[key], tags=instance_tags)
                else:
                    self.log.warn('Missing key {} in stats.'.format(key))

        # Gather store metrics
        store_response = self._get_store_metrics(url, ssl_params, timeout, critical_tags)
        if store_response is not None:
            for key in self.STORE_RATES:
                if key in store_response:
                    self.rate(self.STORE_RATES[key], store_response[key], tags=instance_tags)
                else:
                    self.log.warn('Missing key {} in stats.'.format(key))

            for key in self.STORE_GAUGES:
                if key in store_response:
                    self.gauge(self.STORE_GAUGES[key], store_response[key], tags=instance_tags)
                else:
                    self.log.warn('Missing key {} in stats.'.format(key))

        # Gather leader metrics
        if is_leader:
            leader_response = self._get_leader_metrics(url, ssl_params, timeout, critical_tags)
            if leader_response is not None and len(leader_response.get("followers", {})) > 0:
                # Get the followers
                followers = leader_response.get("followers")
                for fol in followers:
                    # counts
                    for key in self.LEADER_COUNTS:
                        self.rate(self.LEADER_COUNTS[key],
                                  followers[fol].get("counts").get(key),
                                  tags=instance_tags + ['follower:{}'.format(fol)])
                    # latency
                    for key in self.LEADER_LATENCY:
                        self.gauge(self.LEADER_LATENCY[key],
                                   followers[fol].get("latency").get(key),
                                   tags=instance_tags + ['follower:{}'.format(fol)])

        # Service check
        if self_response is not None and store_response is not None:
            self.service_check(self.SERVICE_CHECK_NAME, self.OK,
                               tags=instance_tags)

    def _get_health_status(self, url, ssl_params, timeout):
        """
        Don't send the "can connect" service check if we have troubles getting
        the health status
        """
        try:
            r = self._perform_request(url, "/health", ssl_params, timeout)
            # we don't use get() here so we can report a KeyError
            return r.json()[self.HEALTH_KEY]
        except Exception as e:
            self.log.debug("Can't determine health status: {}".format(e))

    def _get_self_metrics(self, url, ssl_params, timeout, tags):
        return self._get_json(url, "/v2/stats/self", ssl_params, timeout, tags)

    def _get_store_metrics(self, url, ssl_params, timeout, tags):
        return self._get_json(url, "/v2/stats/store", ssl_params, timeout, tags)

    def _get_leader_metrics(self, url, ssl_params, timeout, tags):
        return self._get_json(url, "/v2/stats/leader", ssl_params, timeout, tags)

    def _perform_request(self, url, path, ssl_params, timeout):
        certificate = None
        if 'ssl_certfile' in ssl_params and 'ssl_keyfile' in ssl_params:
            certificate = (ssl_params['ssl_certfile'], ssl_params['ssl_keyfile'])

        verify = ssl_params.get('ssl_ca_certs', True) if ssl_params['ssl_cert_validation'] else False

        return requests.get(
            url + path, verify=verify, cert=certificate, timeout=timeout, headers=headers(self.agentConfig)
        )

    def _get_json(self, url, path, ssl_params, timeout, tags):
        try:
            r = self._perform_request(url, path, ssl_params, timeout)
        except requests.exceptions.Timeout:
            self.service_check(self.SERVICE_CHECK_NAME, self.CRITICAL,
                               message='Timeout when hitting {}'.format(url),
                               tags=tags + ['url:{}'.format(url)])
            raise
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, self.CRITICAL,
                               message='Error hitting {}. Error: {}'.format(url, str(e)),
                               tags=tags + ['url:{}'.format(url)])
            raise

        if r.status_code != 200:
            self.service_check(self.SERVICE_CHECK_NAME, self.CRITICAL,
                               message='Got {} when hitting {}'.format(r.status_code, url),
                               tags=tags + ['url:{}'.format(url)])
            raise Exception('Http status code {} on url {}'.format(r.status_code, url))

        return r.json()

    @classmethod
    def _is_healthy(cls, status):
        """
        Version of etcd prior to 3.3 return this payload when you hit /health:
          {"health": "true"}

        which is wrong since the value is a `bool` on etcd.

        Version 3.3 fixed this issue in https://github.com/coreos/etcd/pull/8312
        but we need to support both.
        """
        if isinstance(status, bool):
            return status

        return status == "true"
