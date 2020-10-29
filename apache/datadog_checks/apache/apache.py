# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck


class Apache(AgentCheck):
    """Tracks basic connection/requests/workers metrics

    See http://httpd.apache.org/docs/2.2/mod/mod_status.html for more details
    """

    GAUGES = {
        'IdleWorkers': 'apache.performance.idle_workers',
        'BusyWorkers': 'apache.performance.busy_workers',
        'CPULoad': 'apache.performance.cpu_load',
        'Uptime': 'apache.performance.uptime',
        'Total kBytes': 'apache.net.bytes',
        'Total Accesses': 'apache.net.hits',
        'ConnsTotal': 'apache.conns_total',
        'ConnsAsyncWriting': 'apache.conns_async_writing',
        'ConnsAsyncKeepAlive': 'apache.conns_async_keep_alive',
        'ConnsAsyncClosing': 'apache.conns_async_closing',
    }

    RATES = {'Total kBytes': 'apache.net.bytes_per_s', 'Total Accesses': 'apache.net.request_per_s'}

    HTTP_CONFIG_REMAPPER = {
        'apache_user': {'name': 'username'},
        'apache_password': {'name': 'password'},
        'disable_ssl_validation': {'name': 'tls_verify', 'invert': True, 'default': False},
        'receive_timeout': {'name': 'read_timeout', 'default': 15},
        'connect_timeout': {'name': 'connect_timeout', 'default': 5},
    }

    VERSION_REGEX = re.compile(r'Apache/(\d+(?:\.\d+)*)')

    def __init__(self, name, init_config, instances):
        super(Apache, self).__init__(name, init_config, instances)
        self.assumed_url = {}

    def check(self, _):
        if 'apache_status_url' not in self.instance:
            raise Exception("Missing 'apache_status_url' in Apache config")

        url = self.assumed_url.get(self.instance['apache_status_url'], self.instance['apache_status_url'])
        tags = self.instance.get('tags', [])

        # Submit a service check for status page availability.
        parsed_url = urlparse(url)
        apache_host = parsed_url.hostname
        apache_port = parsed_url.port or 80
        service_check_name = 'apache.can_connect'
        service_check_tags = ['host:%s' % apache_host, 'port:%s' % apache_port] + tags
        try:
            self.log.debug(
                'apache check initiating request, connect timeout %d receive %d',
                self.http.options['timeout'][0],
                self.http.options['timeout'][1],
            )

            r = self.http.get(url)
            r.raise_for_status()

        except Exception as e:
            self.log.warning("Caught exception %s", e)
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=service_check_tags)
            raise
        else:
            self.service_check(service_check_name, AgentCheck.OK, tags=service_check_tags)

        self.log.debug("apache check succeeded")
        metric_count = 0
        version_submitted = False
        # Loop through and extract the numerical values
        for line in r.iter_lines(decode_unicode=True):
            values = line.split(': ')
            if len(values) == 2:  # match
                metric, value = values
                # Special case: fetch and submit the version
                if metric == 'ServerVersion':
                    self._submit_metadata(value)
                    version_submitted = True
                    continue
                try:
                    value = float(value)
                except ValueError:
                    continue

                # Special case: kBytes => bytes
                if metric == 'Total kBytes':
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

        if metric_count == 0:
            if self.assumed_url.get(self.instance['apache_status_url']) is None and url[-5:] != '?auto':
                self.assumed_url[self.instance['apache_status_url']] = '%s?auto' % url
                self.warning("Assuming url was not correct. Trying to add ?auto suffix to the url")
                self.check(self.instance)
                return
            else:
                raise Exception(
                    ("No metrics were fetched for this instance. Make sure that %s is the proper url.")
                    % self.instance['apache_status_url']
                )

        if not version_submitted:
            # Can't get it from the mod_status output, try to get it from the server header even though
            # it may not be exposed with some configurations.
            server_version = r.headers.get("Server")
            if server_version:
                self._submit_metadata(server_version)

    def _submit_metadata(self, value):
        """Possible formats:
        Apache | Apache/X | Apache/X.Y | Apache/X.Y.Z | Apache/X.Y.Z (<OS>) | Apache/X.Y.Z (<OS>) <not specified>
        https://httpd.apache.org/docs/2.4/mod/core.html#servertokens
        """
        match = self.VERSION_REGEX.match(value)

        if not match or not match.groups():
            self.log.info("Cannot parse the complete Apache version from %s.", value)
            return

        version = match.group(1)
        version_parts = {name: part for name, part in zip(('major', 'minor', 'patch'), version.split('.'))}
        self.set_metadata('version', version, scheme='parts', final_scheme='semver', part_map=version_parts)
        self.log.debug("found apache version %s", version)
