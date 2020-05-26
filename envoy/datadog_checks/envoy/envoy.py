# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import re
from collections import defaultdict

import requests
from six.moves.urllib.parse import urljoin

from datadog_checks.base import AgentCheck

from .errors import UnknownMetric, UnknownTags
from .parser import parse_histogram, parse_metric

LEGACY_VERSION_RE = re.compile(r'/(\d.\d.\d)/')


class Envoy(AgentCheck):
    HTTP_CONFIG_REMAPPER = {'verify_ssl': {'name': 'tls_verify'}}
    SERVICE_CHECK_NAME = 'envoy.can_connect'

    def __init__(self, name, init_config, instances):
        super(Envoy, self).__init__(name, init_config, instances)
        self.unknown_metrics = defaultdict(int)
        self.unknown_tags = defaultdict(int)
        self.whitelist = None
        self.blacklist = None

        # The memory implications here are unclear to me. We may want a bloom filter
        # or a data structure that expires elements based on inactivity.
        self.whitelisted_metrics = set()
        self.blacklisted_metrics = set()

        self.caching_metrics = None

    def check(self, instance):
        custom_tags = instance.get('tags', [])

        try:
            stats_url = instance['stats_url']
        except KeyError:
            msg = 'Envoy configuration setting `stats_url` is required'
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=msg, tags=custom_tags)
            self.log.error(msg)
            return

        if self.whitelist is None:
            whitelist = set(re.sub(r'^envoy\\?\.', '', s, 1) for s in instance.get('metric_whitelist', []))
            self.whitelist = [re.compile(pattern) for pattern in whitelist]

        if self.blacklist is None:
            blacklist = set(re.sub(r'^envoy\\?\.', '', s, 1) for s in instance.get('metric_blacklist', []))
            self.blacklist = [re.compile(pattern) for pattern in blacklist]

        if self.caching_metrics is None:
            self.caching_metrics = instance.get('cache_metrics', True)

        self._collect_metadata(stats_url)

        try:
            response = self.http.get(stats_url)
        except requests.exceptions.Timeout:
            timeout = self.http.options['timeout']
            msg = 'Envoy endpoint `{}` timed out after {} seconds'.format(stats_url, timeout)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=msg, tags=custom_tags)
            self.log.exception(msg)
            return
        except (requests.exceptions.RequestException, requests.exceptions.ConnectionError):
            msg = 'Error accessing Envoy endpoint `{}`'.format(stats_url)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=msg, tags=custom_tags)
            self.log.exception(msg)
            return

        if response.status_code != 200:
            msg = 'Envoy endpoint `{}` responded with HTTP status code {}'.format(stats_url, response.status_code)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=msg, tags=custom_tags)
            self.log.warning(msg)
            return

        # Avoid repeated global lookups.
        get_method = getattr

        for line in response.content.decode().splitlines():
            try:
                envoy_metric, value = line.split(': ')
            except ValueError:
                continue

            if not self.whitelisted_metric(envoy_metric):
                continue

            try:
                metric, tags, method = parse_metric(envoy_metric)
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

            tags.extend(custom_tags)

            try:
                value = int(value)
                get_method(self, method)(metric, value, tags=tags)

            # If the value isn't an integer assume it's pre-computed histogram data.
            except (ValueError, TypeError):
                for metric, value in parse_histogram(metric, value):
                    self.gauge(metric, value, tags=tags)

        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=custom_tags)

    def whitelisted_metric(self, metric):
        if self.caching_metrics:
            if metric in self.whitelisted_metrics:
                return True
            elif metric in self.blacklisted_metrics:
                return False

        if self.whitelist:
            whitelisted = any(pattern.search(metric) for pattern in self.whitelist)
            if self.blacklist:
                whitelisted = whitelisted and not any(pattern.search(metric) for pattern in self.blacklist)

            if self.caching_metrics and whitelisted:
                self.whitelisted_metrics.add(metric)

            return whitelisted
        elif self.blacklist:
            blacklisted = any(pattern.search(metric) for pattern in self.blacklist)

            if self.caching_metrics and blacklisted:
                self.blacklisted_metrics.add(metric)

            return not blacklisted
        else:
            return True

    @AgentCheck.metadata_entrypoint
    def _collect_metadata(self, stats_url):
        # From http://domain/thing/stats to http://domain/thing/server_info
        server_info_url = urljoin(stats_url, 'server_info')
        raw_version = None

        try:
            response = self.http.get(server_info_url)
            if response.status_code != 200:
                msg = 'Envoy endpoint `{}` responded with HTTP status code {}'.format(
                    server_info_url, response.status_code
                )
                self.log.info(msg)
                return
            # {
            #   "version": "222aaacccfff888/1.14.1/Clean/RELEASE/BoringSSL",
            #   "state": "LIVE",
            #   ...
            # }
            try:
                raw_version = response.json()["version"].split('/')[1]
            except json.decoder.JSONDecodeError as e:
                self.log.debug('Error decoding json for with url=`%s`. Error: %s', server_info_url, str(e))

            if raw_version is None:
                # Search version in server info for Envoy version <= 1.8
                # Example:
                #     envoy 5d25f466c3410c0dfa735d7d4358beb76b2da507/1.8.0/Clean/RELEASE live 581130 581130 0
                content = response.content.decode()
                found = LEGACY_VERSION_RE.search(content)
                if found:
                    raw_version = found.group(1)
                else:
                    self.log.debug('Version not matched. content=%s', content)
                    return

        except requests.exceptions.Timeout:
            self.log.warning(
                'Envoy endpoint `%s` timed out after %s seconds', server_info_url, self.http.options['timeout']
            )
            return
        except Exception as e:
            self.log.warning('Error collecting Envoy version with url=`%s`. Error: %s', server_info_url, str(e))
            return

        if raw_version:
            self.set_metadata('version', raw_version)
