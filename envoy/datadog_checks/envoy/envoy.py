# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import defaultdict

import requests

from datadog_checks.checks import AgentCheck

from .errors import UnknownMetric, UnknownTags
from .parser import parse_histogram, parse_metric


class Envoy(AgentCheck):
    SERVICE_CHECK_NAME = 'envoy.can_connect'

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(Envoy, self).__init__(name, init_config, agentConfig, instances)
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

        username = instance.get('username', None)
        password = instance.get('password', None)
        auth = (username, password) if username and password else None
        verify_ssl = instance.get('verify_ssl', True)
        proxies = self.get_instance_proxy(instance, stats_url)
        timeout = int(instance.get('timeout', 20))

        if self.whitelist is None:
            whitelist = set(re.sub(r'^envoy\\?\.', '', s, 1) for s in instance.get('metric_whitelist', []))
            self.whitelist = [re.compile(pattern) for pattern in whitelist]

        if self.blacklist is None:
            blacklist = set(re.sub(r'^envoy\\?\.', '', s, 1) for s in instance.get('metric_blacklist', []))
            self.blacklist = [re.compile(pattern) for pattern in blacklist]

        if self.caching_metrics is None:
            self.caching_metrics = instance.get('cache_metrics', True)

        try:
            response = requests.get(
                stats_url, auth=auth, verify=verify_ssl, proxies=proxies, timeout=timeout
            )
        except requests.exceptions.Timeout:
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
                    self.log.debug('Unknown metric `{}`'.format(envoy_metric))
                self.unknown_metrics[envoy_metric] += 1
                continue
            except UnknownTags as e:
                unknown_tags = str(e).split('|||')
                for tag in unknown_tags:
                    if tag not in self.unknown_tags:
                        self.log.debug('Unknown tag `{}` in metric `{}`'.format(tag, envoy_metric))
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
