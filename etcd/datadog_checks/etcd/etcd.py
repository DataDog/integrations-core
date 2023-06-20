# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six.moves.urllib.parse import urlparse

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck, is_affirmative

from .metrics import METRIC_MAP


class Etcd(OpenMetricsBaseCheck):
    DEFAULT_METRIC_LIMIT = 0

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

        self.HTTP_CONFIG_REMAPPER = {
            'ssl_cert': {'name': 'tls_cert'},
            'ssl_private_key': {'name': 'tls_private_key'},
            'ssl_ca_cert': {'name': 'tls_ca_cert'},
            'ssl_verify': {'name': 'tls_verify'},
            'prometheus_timeout': {'name': 'timeout'},
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

    def check(self, _):
        scraper_config = self.get_scraper_config(self.instance)

        if 'prometheus_url' not in scraper_config:
            raise ConfigurationError('You have to define at least one `prometheus_url`.')

        if not scraper_config.get('metrics_mapper'):
            raise ConfigurationError(
                'You have to collect at least one metric from the endpoint `{}`.'.format(
                    scraper_config['prometheus_url']
                )
            )

        tags = []

        if is_affirmative(self.instance.get('leader_tag', True)):
            self.add_leader_state_tag(scraper_config, tags)

        scraper_config['_metric_tags'][:] = tags

        self.process(scraper_config)

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
        response = self.access_api(scraper_config, '/v3/maintenance/status')

        leader = response.get('leader')
        member = response.get('header', {}).get('member_id')

        return leader and member and leader == member

    def add_leader_state_tag(self, scraper_config, tags):
        is_leader = self.is_leader(scraper_config)

        if is_leader is not None:
            tags.append('is_leader:{}'.format('true' if is_leader else 'false'))

    def transform_metadata(self, metric, scraper_config):
        super(Etcd, self).transform_metadata(metric, scraper_config)

        # Needed for backward compatibility, we continue to submit `etcd.server.version` metric
        self.submit_openmetric('server.version', metric, scraper_config)

    def _perform_request(self, url, path):
        return self.http.get(url + path)
