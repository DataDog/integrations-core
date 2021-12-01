# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import re

from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck

VERSION_REGEX = re.compile(r".*/((\d+).*)")


class Lighttpd(AgentCheck):
    """Tracks basic connection/requests/workers metrics

    See http://redmine.lighttpd.net/projects/1/wiki/Docs_ModStatus for Lighttpd details
    See http://redmine.lighttpd.net/projects/lighttpd2/wiki/Mod_status for Lighttpd2 details
    """

    SERVICE_CHECK_NAME = 'lighttpd.can_connect'

    URL_SUFFIX_PER_VERSION = {1: '?auto', 2: '?format=plain', 'Unknown': '?auto'}

    GAUGES = {
        b'IdleServers': 'lighttpd.performance.idle_server',
        b'BusyServers': 'lighttpd.performance.busy_servers',
        b'Uptime': 'lighttpd.performance.uptime',
        b'Total kBytes': 'lighttpd.net.bytes',
        b'Total Accesses': 'lighttpd.net.hits',
        b'memory_usage': 'lighttpd.performance.memory_usage',
        b'requests_avg': 'lighttpd.net.requests_avg',
        b'traffic_out_avg': 'lighttpd.net.bytes_out_avg',
        b'traffic_in_avg': 'lighttpd.net.bytes_in_avg',
        b'connections_avg': 'lighttpd.net.connections_avg',
        b'connection_state_start': 'lighttpd.connections.state_start',
        b'connection_state_read_header': 'lighttpd.connections.state_read_header',
        b'connection_state_handle_request': 'lighttpd.connections.state_handle_request',
        b'connection_state_write_response': 'lighttpd.connections.state_write_response',
        b'connection_state_keep_alive': 'lighttpd.connections.state_keep_alive',
        b'requests_avg_5sec': 'lighttpd.net.requests_avg_5sec',
        b'traffic_out_avg_5sec': 'lighttpd.net.bytes_out_avg_5sec',
        b'traffic_in_avg_5sec': 'lighttpd.net.bytes_in_avg_5sec',
        b'connections_avg_5sec': 'lighttpd.net.connections_avg_5sec',
    }

    COUNTERS = {
        b'requests_abs': 'lighttpd.net.requests_total',
        b'traffic_out_abs': 'lighttpd.net.bytes_out',
        b'traffic_in_abs': 'lighttpd.net.bytes_in',
        b'connections_abs': 'lighttpd.net.connections_total',
        b'status_1xx': 'lighttpd.response.status_1xx',
        b'status_2xx': 'lighttpd.response.status_2xx',
        b'status_3xx': 'lighttpd.response.status_3xx',
        b'status_4xx': 'lighttpd.response.status_4xx',
        b'status_5xx': 'lighttpd.response.status_5xx',
    }

    RATES = {b'Total kBytes': 'lighttpd.net.bytes_per_s', b'Total Accesses': 'lighttpd.net.request_per_s'}

    HTTP_CONFIG_REMAPPER = {'user': {'name': 'username'}}

    def __init__(self, name, init_config, instances):
        super(Lighttpd, self).__init__(name, init_config, instances)
        self.assumed_url = {}

    def check(self, instance):
        if 'lighttpd_status_url' not in instance:
            raise Exception("Missing 'lighttpd_status_url' variable in Lighttpd config")

        url = self.assumed_url.get(instance['lighttpd_status_url'], instance['lighttpd_status_url'])

        tags = instance.get('tags', [])

        self.log.debug("Connecting to %s", url)

        # Submit a service check for status page availability.
        parsed_url = urlparse(url)
        lighttpd_url = parsed_url.hostname
        lighttpd_port = parsed_url.port or 80
        service_check_tags = ['host:%s' % lighttpd_url, 'port:%s' % lighttpd_port] + tags
        try:
            r = self.http.get(url)
            r.raise_for_status()
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags)
            raise
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)

        headers_resp = r.headers
        full_version, server_version = self._get_server_version(headers_resp)
        if full_version is not None:
            self.set_metadata('version', full_version)
        else:
            self.log.debug("Lighttpd version %s not found", full_version)

        response = r.content

        metric_count = 0
        # Loop through and extract the numerical values
        for line in response.split(b'\n'):
            values = line.split(b': ')
            if len(values) == 2:  # match
                metric, value = values
                try:
                    value = float(value)
                except ValueError:
                    continue

                # Special case: kBytes => bytes
                if metric == b'Total kBytes':
                    value = value * 1024

                # Send metric as a gauge, if applicable
                if metric in self.GAUGES:
                    metric_count += 1
                    metric_name = self.GAUGES[metric]
                    self.gauge(metric_name, value, tags=tags)

                # Send metric as a rate, if applicable
                if metric in self.RATES:
                    metric_count += 1
                    metric_name = self.RATES[metric]
                    self.rate(metric_name, value, tags=tags)

                # Send metric as a counter, if applicable
                if metric in self.COUNTERS:
                    metric_count += 1
                    metric_name = self.COUNTERS[metric]
                    self.increment(metric_name, value, tags=tags)

        if metric_count == 0:
            url_suffix = self.URL_SUFFIX_PER_VERSION[server_version]
            if self.assumed_url.get(instance['lighttpd_status_url']) is None and url[-len(url_suffix) :] != url_suffix:
                self.assumed_url[instance['lighttpd_status_url']] = '%s%s' % (url, url_suffix)
                self.warning("Assuming url was not correct. Trying to add %s suffix to the url", url_suffix)
                self.check(instance)
            else:
                raise Exception(
                    "No metrics were fetched for this instance. Make sure "
                    "that %s is the proper url." % instance['lighttpd_status_url']
                )

    def _get_server_version(self, headers):
        server_version = headers.get("server", "")

        match = VERSION_REGEX.match(server_version)
        if match is None:
            self.log.debug("Lighttpd server version is Unknown")
            return None, "Unknown"

        full_version = match.group(1)
        server_version = int(match.group(2))
        self.log.debug("Lighttpd server version is %s", server_version)
        return full_version, server_version
