# (C) Datadog, Inc. 2018-present
# (C)  graemej <graeme.johnson@jadedpixel.com> 2014
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import requests
from six import iteritems
from six.moves.urllib.parse import urljoin

from datadog_checks.base import AgentCheck


class Marathon(AgentCheck):

    DEFAULT_TIMEOUT = 5
    SERVICE_CHECK_NAME = 'marathon.can_connect'
    ACS_TOKEN = None

    APP_METRICS = [
        'backoffFactor',
        'backoffSeconds',
        'cpus',
        'disk',
        'instances',
        'mem',
        'taskRateLimit',
        'tasksRunning',
        'tasksStaged',
        'tasksHealthy',
        'tasksUnhealthy',
    ]

    QUEUE_METRICS = {
        'count': (None, 'count'),
        'delay': ('timeLeftSeconds', 'delay'),
        'processedOffersSummary': [
            ('processedOffersCount', 'offers.processed'),
            ('unusedOffersCount', 'offers.unused'),
            ('rejectSummaryLastOffers', 'offers.reject.last'),
            ('rejectSummaryLaunchAttempt', 'offers.reject.launch'),
        ],
    }

    QUEUE_PREFIX = 'marathon.queue'

    HTTP_CONFIG_REMAPPER = {
        'user': {'name': 'username'},
        'disable_ssl_validation': {'name': 'tls_verify', 'invert': True, 'default': False},
    }

    def __init__(self, name, init_config, instances):
        super(Marathon, self).__init__(name, init_config, instances)
        timeout = (
            self.instance.get('timeout')
            or self.init_config.get('timeout')
            or self.init_config.get('default_timeout')
            or self.DEFAULT_TIMEOUT
        )
        if not ('read_timeout' in self.instance or 'connect_timeout' in self.instance):
            # `default_timeout` config option will be removed with Agent 5
            self.http.options['timeout'] = timeout
        else:
            self.http.options['timeout'] = (
                float(self.instance.get('read_timeout', timeout)),
                float(self.instance.get('connect_timeout', timeout)),
            )
        self._auth_body = None
        if self.http.options['auth'] is not None:
            self._auth_body = {'uid': self.http.options['auth'][0], 'password': self.http.options['auth'][1]}

    def check(self, instance):
        try:
            url, acs_url, group, instance_tags, label_tags = self.get_instance_config(instance)
        except Exception as e:
            self.log.error("Invalid instance configuration.")
            raise e

        self.apps_response = None
        self.process_apps(url, acs_url, instance_tags, label_tags, group)
        self.process_deployments(url, acs_url, instance_tags)
        self.process_queues(url, acs_url, instance_tags, label_tags)

    def refresh_acs_token(self, acs_url, tags=None):
        if tags is None:
            tags = []

        try:
            r = self.http.post(urljoin(acs_url, "acs/api/v1/auth/login"), json=self._auth_body, verify=False)
            r.raise_for_status()
            token = r.json()['token']
            self.ACS_TOKEN = token
            return token
        except requests.exceptions.HTTPError:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message="acs auth url {} returned a status of {}".format(acs_url, r.status_code),
                tags=["url:{}".format(acs_url)] + tags,
            )
            raise Exception("Got %s when hitting %s" % (r.status_code, acs_url))

    def get_json(self, url, acs_url, tags=None):
        if tags is None:
            tags = []

        if acs_url:
            # If the ACS token has not been set, go get it
            if not self.ACS_TOKEN:
                self.refresh_acs_token(acs_url, tags)
            self.http.options['headers']['authorization'] = 'token={}'.format(self.ACS_TOKEN)

        try:
            r = self.http.get(url)
            # If got unauthorized and using acs auth, refresh the token and try again
            if r.status_code == 401 and acs_url:
                self.refresh_acs_token(acs_url, tags)
                r = self.http.get(url)
            r.raise_for_status()
        except requests.exceptions.Timeout:
            # If there's a timeout
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message="{} timed out after {} seconds.".format(url, self.http.options['timeout'][0]),
                tags=["url:{}".format(url)] + tags,
            )
            raise Exception("Timeout when hitting {}".format(url))

        except requests.exceptions.HTTPError:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message="{} returned a status of {}".format(url, r.status_code),
                tags=["url:{}".format(url)] + tags,
            )
            raise Exception("Got {} when hitting {}".format(r.status_code, url))

        except requests.exceptions.ConnectionError:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message="{} Connection Refused.".format(url),
                tags=["url:{}".format(url)] + tags,
            )
            raise Exception("Connection refused when hitting {}".format(url))

        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=["url:{}".format(url)] + tags)

        return r.json()

    def get_instance_config(self, instance):
        if 'url' not in instance:
            raise Exception('Marathon instance missing "url" value.')

        # Load values from the instance config
        url = instance['url']
        acs_url = instance.get('acs_url')
        group = instance.get('group')

        tags = instance.get('tags', [])
        label_tags = instance.get('label_tags', [])

        return url, acs_url, group, tags, label_tags

    def get_apps_json(self, url, acs_url, tags, group):
        """
        The dictionary containing the apps is cached during collection and reset
        at every `check()` call.
        """
        if self.apps_response is not None:
            return self.apps_response

        # Marathon apps
        if group is None:
            # embed=apps.counts is not a required parameter but will be in the future:
            # http://mesosphere.github.io/marathon/1.4/docs/rest-api.html#get-v2apps
            marathon_path = urljoin(url, "v2/apps?embed=apps.counts")
        else:
            marathon_path = urljoin(
                url, "v2/groups/{}?embed=group.groups".format(group) + "&embed=group.apps&embed=group.apps.counts"
            )

        self.apps_response = self.get_json(marathon_path, acs_url, tags)
        return self.apps_response

    def process_apps(self, url, acs_url, tags, label_tags, group):
        response = self.get_apps_json(url, acs_url, tags, group)
        if response is None:
            return

        self.gauge('marathon.apps', len(response['apps']), tags=tags)
        for app in response['apps']:
            app_tags = self.get_app_tags(app, tags, label_tags)
            for attr in self.APP_METRICS:
                if attr in app:
                    self.gauge('marathon.' + attr, app[attr], tags=app_tags)

    def process_deployments(self, url, acs_url, tags=None):
        # Number of running/pending deployments
        response = self.get_json(urljoin(url, "v2/deployments"), acs_url, tags)
        if response is not None:
            self.gauge('marathon.deployments', len(response), tags=tags)

    def process_queues(self, url, acs_url, tags=None, label_tags=None, group=None):
        response = self.get_json(urljoin(url, "v2/queue"), acs_url, tags)
        if response is None:
            return

        # Number of queued applications
        self.gauge('{}.size'.format(self.QUEUE_PREFIX), len(response['queue']), tags=tags)

        queued = set()

        for queue in response['queue']:
            q_tags = self.get_app_tags(queue['app'], tags, label_tags)

            queued.add(queue['app']['id'])

            for m_type, sub_metric in iteritems(self.QUEUE_METRICS):
                if isinstance(sub_metric, list):
                    for attr, name in sub_metric:
                        try:
                            metric_name = '{}.{}'.format(self.QUEUE_PREFIX, name)
                            _attr = queue[m_type][attr]
                            if 'Summary' in attr:
                                for reject in _attr:
                                    reason = reject['reason']
                                    declined = reject['declined']
                                    processed = reject['processed']
                                    summary_tags = q_tags + ['reason:{}'.format(reason)]
                                    self.gauge(metric_name, declined, tags=summary_tags + ['status:declined'])
                                    self.gauge(metric_name, processed, tags=summary_tags + ['status:processed'])
                            else:
                                val = float(_attr)
                                self.gauge(metric_name, val, tags=q_tags)
                        except (KeyError, TypeError):
                            self.log.warning("Metric unavailable skipping: %s", metric_name)

                else:
                    try:
                        attr, name = sub_metric
                        metric_name = '{}.{}'.format(self.QUEUE_PREFIX, name)
                        _attr = queue[m_type][attr] if attr else queue[m_type]
                        val = float(_attr)
                        self.gauge(metric_name, val, tags=q_tags)
                    except (KeyError, TypeError):
                        self.log.warning("Metric unavailable skipping: %s", metric_name)

        self.ensure_queue_count(queued, url, acs_url, tags, label_tags, group)

    def get_app_tags(self, app, tags=None, label_tags=None):
        if tags is None:
            tags = []
        if label_tags is None:
            label_tags = []

        basic_tags = ['app_id:{}'.format(app['id']), 'version:{}'.format(app['version'])]

        label_tag_values = []
        for label_name in label_tags:
            try:
                label_value = app['labels'][label_name]
                label_tag_values.append('{}:{}'.format(label_name, label_value))
            except KeyError:
                pass

        basic_tags.extend(tags)
        basic_tags.extend(label_tag_values)

        return basic_tags

    def ensure_queue_count(self, queued, url, acs_url, tags=None, label_tags=None, group=None):
        """
        Ensure `marathon.queue.count` is reported as zero for apps without queued instances.
        """
        metric_name = '{}.count'.format(self.QUEUE_PREFIX)

        apps_response = self.get_apps_json(url, acs_url, tags, group)

        for app in apps_response['apps']:
            if app['id'] not in queued:
                q_tags = self.get_app_tags(app, tags, label_tags)
                self.gauge(metric_name, 0, tags=q_tags)
