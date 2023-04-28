# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import defaultdict

import requests
from six import PY2
from six.moves.urllib.parse import urljoin

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

from .errors import UnknownMetric, UnknownTags
from .parser import parse_histogram, parse_metric
from .utils import _get_server_info


class Envoy(AgentCheck):
    """
    This is a legacy implementation that will be removed at some point, refer to check.py for the new implementation.
    """

    HTTP_CONFIG_REMAPPER = {'verify_ssl': {'name': 'tls_verify'}}
    SERVICE_CHECK_NAME = 'envoy.can_connect'

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if 'openmetrics_endpoint' in instance:
            if PY2:
                raise ConfigurationError(
                    "This version of the integration is only available when using py3. "
                    "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                    "for more information or use the older style config."
                )
            # TODO: when we drop Python 2 move this import up top
            from .check import EnvoyCheckV2

            return EnvoyCheckV2(name, init_config, instances)
        else:
            return super(Envoy, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(Envoy, self).__init__(name, init_config, instances)
        self.unknown_metrics = defaultdict(int)
        self.unknown_tags = defaultdict(int)

        self.custom_tags = self.instance.get('tags', [])
        self.caching_metrics = self.instance.get('cache_metrics', True)

        self.collect_server_info = self.instance.get('collect_server_info', True)
        self.stats_url = self.instance.get('stats_url')
        if self.stats_url is None:
            raise ConfigurationError('Envoy configuration setting `stats_url` is required')

        included_metrics = {
            re.sub(r'^envoy\\?\.', '', s, 1)
            for s in self.instance.get(
                'included_metrics',
                self.instance.get(
                    'metric_whitelist',
                    self.instance.get(
                        'include_metrics',
                        [],
                    ),
                ),
            )
        }
        self.config_included_metrics = [re.compile(pattern) for pattern in included_metrics]

        excluded_metrics = {
            re.sub(r'^envoy\\?\.', '', s, 1)
            for s in self.instance.get(
                'excluded_metrics',
                self.instance.get(
                    'metric_blacklist',
                    self.instance.get(
                        'exclude_metrics',
                        [],
                    ),
                ),
            )
        }
        self.config_excluded_metrics = [re.compile(pattern) for pattern in excluded_metrics]

        # The memory implications here are unclear to me. We may want a bloom filter
        # or a data structure that expires elements based on inactivity.
        self.included_metrics_cache = set()
        self.excluded_metrics_cache = set()

        self.caching_metrics = None
        self.parse_unknown_metrics = is_affirmative(self.instance.get('parse_unknown_metrics', False))
        self.disable_legacy_cluster_tag = is_affirmative(self.instance.get('disable_legacy_cluster_tag', False))

    def check(self, _):
        self._collect_metadata()

        try:
            response = self.http.get(self.stats_url)
        except requests.exceptions.Timeout:
            timeout = self.http.options['timeout']
            msg = 'Envoy endpoint `{}` timed out after {} seconds'.format(self.stats_url, timeout)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=msg, tags=self.custom_tags)
            self.log.exception(msg)
            return
        except (requests.exceptions.RequestException, requests.exceptions.ConnectionError):
            msg = 'Error accessing Envoy endpoint `{}`'.format(self.stats_url)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=msg, tags=self.custom_tags)
            self.log.exception(msg)
            return

        if response.status_code != 200:
            msg = 'Envoy endpoint `{}` responded with HTTP status code {}'.format(self.stats_url, response.status_code)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=msg, tags=self.custom_tags)
            self.log.warning(msg)
            return

        # Avoid repeated global lookups.
        get_method = getattr

        for line in response.content.decode().splitlines():
            try:
                envoy_metric, value = line.split(': ')
            except ValueError:
                continue

            if not self.included_metrics(envoy_metric):
                continue

            try:
                metric, tags, method = parse_metric(
                    envoy_metric,
                    retry=self.parse_unknown_metrics,
                    disable_legacy_cluster_tag=self.disable_legacy_cluster_tag,
                )
            except UnknownMetric:
                if envoy_metric not in self.unknown_metrics:
                    self.log.debug('Unknown metric `%s`', envoy_metric)
                self.unknown_metrics[envoy_metric] += 1
                continue
            except UnknownTags as e:
                unknown_tags = str(e).split('|||')
                for tag in unknown_tags:
                    if tag not in self.unknown_tags:
                        self.log.debug('Unknown tag `%s` in metric `%s`', tag, envoy_metric)
                    self.unknown_tags[tag] += 1
                continue

            tags.extend(self.custom_tags)

            try:
                value = int(value)
                get_method(self, method)(metric, value, tags=tags)

            # If the value isn't an integer assume it's pre-computed histogram data.
            except (ValueError, TypeError):
                for histo_metric, histo_value in parse_histogram(metric, value):
                    self.gauge(histo_metric, histo_value, tags=tags)

        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.custom_tags)

    def included_metrics(self, metric):
        if self.caching_metrics:
            if metric in self.included_metrics_cache:
                return True
            elif metric in self.excluded_metrics_cache:
                return False

        if self.config_included_metrics:
            included_metrics = any(pattern.search(metric) for pattern in self.config_included_metrics)
            if self.config_excluded_metrics:
                included_metrics = included_metrics and not any(
                    pattern.search(metric) for pattern in self.config_excluded_metrics
                )

            if self.caching_metrics and included_metrics:
                self.included_metrics_cache.add(metric)

            return included_metrics
        elif self.config_excluded_metrics:
            excluded_metrics = any(pattern.search(metric) for pattern in self.config_excluded_metrics)

            if self.caching_metrics and excluded_metrics:
                self.excluded_metrics_cache.add(metric)

            return not excluded_metrics
        else:
            return True

    @AgentCheck.metadata_entrypoint
    def _collect_metadata(self):
        if not self.collect_server_info:
            self.log.debug("Skipping server info collection because collect_server_info was disabled")
            return
        # From http://domain/thing/stats to http://domain/thing/server_info
        server_info_url = urljoin(self.stats_url, 'server_info')
        raw_version = _get_server_info(server_info_url, self.log, self.http)

        if raw_version:
            self.set_metadata('version', raw_version)
