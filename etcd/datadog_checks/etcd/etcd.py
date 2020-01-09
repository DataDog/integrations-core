# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests
from six.moves.urllib.parse import urlparse

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck, is_affirmative

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
        'expireCount': 'etcd.store.expire.count',
    }

    STORE_GAUGES = {'watchers': 'etcd.store.watchers'}

    LEADER_GAUGES = {'sendPkgRate': 'etcd.self.send.pkgrate', 'sendBandwidthRate': 'etcd.self.send.bandwidthrate'}

    FOLLOWER_GAUGES = {'recvPkgRate': 'etcd.self.recv.pkgrate', 'recvBandwidthRate': 'etcd.self.recv.bandwidthrate'}

    SELF_RATES = {
        'recvAppendRequestCnt': 'etcd.self.recv.appendrequest.count',
        'sendAppendRequestCnt': 'etcd.self.send.appendrequest.count',
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

    def __init__(self, name, init_config, instances):

        instance = instances[0]
        if is_affirmative(instance.get('use_preview', True)):
            self.HTTP_CONFIG_REMAPPER = {
                'ssl_cert': {'name': 'tls_cert'},
                'ssl_private_key': {'name': 'tls_private_key'},
                'ssl_ca_cert': {'name': 'tls_ca_cert'},
                'ssl_verify': {'name': 'tls_verify'},
                'prometheus_timeout': {'name': 'timeout'},
            }
        else:
            # For legacy check ensure prometheus_url is set so
            # OpenMetricsBaseCheck instantiation succeeds
            instance.setdefault('prometheus_url', '')
            self.HTTP_CONFIG_REMAPPER = {
                'ssl_keyfile': {'name': 'tls_private_key'},
                'ssl_certfile': {'name': 'tls_cert'},
                'ssl_cert_validation': {'name': 'tls_verify'},
                'ssl_ca_certs': {'name': 'tls_ca_cert'},
            }

        super(Etcd, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                'etcd': {
                    'prometheus_url': 'http://localhost:2379/metrics',
                    'namespace': 'etcd',
                    'metrics': [METRIC_MAP],
                    'send_histograms_buckets': True,
                    'metadata_metric_name': 'etcd_server_version',
                    'metadata_label_map': {'version': 'server_version'},
                }
            },
            default_namespace='etcd',
        )

    def check(self, instance):
        if is_affirmative(instance.get('use_preview', True)):
            self.check_post_v3(instance)
        else:
            self.warning('In the future etcd check will only support ETCD v3+.')
            self.check_pre_v3(instance)

    def access_api(self, scraper_config, path, data='{}'):
        url = urlparse(scraper_config['prometheus_url'])
        endpoint = '{}://{}{}'.format(url.scheme, url.netloc, path)

        response = {}
        try:
            r = self.http.post(endpoint, data=data)
            response.update(r.json())
        except Exception as e:
            self.log.debug('Error accessing GRPC gateway: %s', e)

        return response

    def is_leader(self, scraper_config):
        # Modify endpoint as etcd stabilizes
        # https://github.com/etcd-io/etcd/blob/master/Documentation/dev-guide/api_grpc_gateway.md#notes
        response = self.access_api(scraper_config, '/v3alpha/maintenance/status')

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
            raise ConfigurationError('You have to define at least one `prometheus_url`.')

        if not scraper_config.get('metrics_mapper'):
            raise ConfigurationError(
                'You have to collect at least one metric from the endpoint `{}`.'.format(
                    scraper_config['prometheus_url']
                )
            )

        tags = []

        if is_affirmative(instance.get('leader_tag', True)):
            self.add_leader_state_tag(scraper_config, tags)

        scraper_config['_metric_tags'][:] = tags

        self.process(scraper_config)

    def transform_metadata(self, metric, scraper_config):
        super(Etcd, self).transform_metadata(metric, scraper_config)

        # Needed for backward compatibility, we continue to submit `etcd.server.version` metric
        self.submit_openmetric('server.version', metric, scraper_config)

    def check_pre_v3(self, instance):
        if 'url' not in instance:
            raise Exception('etcd instance missing "url" value.')

        # Load values from the instance config
        url = instance['url']
        instance_tags = instance.get('tags', [])

        # Get a copy of tags for the CRIT statuses
        critical_tags = list(instance_tags)

        # Append the instance's URL in case there are more than one, that
        # way they can tell the difference!
        instance_tags.append('url:{}'.format(url))
        timeout = float(instance.get('timeout', self.DEFAULT_TIMEOUT))
        is_leader = False

        # Gather self health status
        sc_state = self.UNKNOWN
        health_status = self._get_health_status(url, timeout)
        if health_status is not None:
            sc_state = self.OK if self._is_healthy(health_status) else self.CRITICAL
        self.service_check(self.HEALTH_SERVICE_CHECK_NAME, sc_state, tags=instance_tags)

        # Gather self metrics
        self_response = self._get_self_metrics(url, critical_tags)
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
                    self.log.warning('Missing key %s in stats.', key)

            for key in gauges:
                if key in self_response:
                    self.gauge(gauges[key], self_response[key], tags=instance_tags)
                else:
                    self.log.warning('Missing key %s in stats.', key)

        # Gather store metrics
        store_response = self._get_store_metrics(url, critical_tags)
        if store_response is not None:
            for key in self.STORE_RATES:
                if key in store_response:
                    self.rate(self.STORE_RATES[key], store_response[key], tags=instance_tags)
                else:
                    self.log.warning('Missing key %s in stats.', key)

            for key in self.STORE_GAUGES:
                if key in store_response:
                    self.gauge(self.STORE_GAUGES[key], store_response[key], tags=instance_tags)
                else:
                    self.log.warning('Missing key %s in stats.', key)

        # Gather leader metrics
        if is_leader:
            leader_response = self._get_leader_metrics(url, critical_tags)
            if leader_response is not None and len(leader_response.get("followers", {})) > 0:
                # Get the followers
                followers = leader_response.get("followers")
                for fol in followers:
                    # counts
                    for key in self.LEADER_COUNTS:
                        self.rate(
                            self.LEADER_COUNTS[key],
                            followers[fol].get("counts").get(key),
                            tags=instance_tags + ['follower:{}'.format(fol)],
                        )
                    # latency
                    for key in self.LEADER_LATENCY:
                        self.gauge(
                            self.LEADER_LATENCY[key],
                            followers[fol].get("latency").get(key),
                            tags=instance_tags + ['follower:{}'.format(fol)],
                        )

        # Service check
        if self_response is not None and store_response is not None:
            self.service_check(self.SERVICE_CHECK_NAME, self.OK, tags=instance_tags)

        self._collect_metadata(url, critical_tags)

    def _get_health_status(self, url, timeout):
        """
        Don't send the "can connect" service check if we have troubles getting
        the health status
        """
        try:
            r = self._perform_request(url, "/health")
            # we don't use get() here so we can report a KeyError
            return r.json()[self.HEALTH_KEY]
        except Exception as e:
            self.log.debug("Can't determine health status: %s", e)

    def _get_self_metrics(self, url, tags):
        return self._get_json(url, "/v2/stats/self", tags)

    def _get_store_metrics(self, url, tags):
        return self._get_json(url, "/v2/stats/store", tags)

    def _get_leader_metrics(self, url, tags):
        return self._get_json(url, "/v2/stats/leader", tags)

    def _perform_request(self, url, path):
        return self.http.get(url + path)

    def _get_json(self, url, path, tags):
        try:
            r = self._perform_request(url, path)
        except requests.exceptions.Timeout:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                self.CRITICAL,
                message='Timeout when hitting {}'.format(url),
                tags=tags + ['url:{}'.format(url)],
            )
            raise
        except Exception as e:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                self.CRITICAL,
                message='Error hitting {}. Error: {}'.format(url, str(e)),
                tags=tags + ['url:{}'.format(url)],
            )
            raise

        if r.status_code != 200:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                self.CRITICAL,
                message='Got {} when hitting {}'.format(r.status_code, url),
                tags=tags + ['url:{}'.format(url)],
            )
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

    def _collect_metadata(self, url, tags):
        resp = self._get_json(url, "/version", tags)
        server_version = resp.get('etcdserver')
        self.log.debug("Agent version is `%s`", server_version)
        if server_version:
            self.set_metadata('version', server_version)
