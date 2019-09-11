# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
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

    def __init__(self, name, init_config, instances):
        super(Apache, self).__init__(name, init_config, instances)
        self.assumed_url = {}

    def check(self, instance):
        try:
            apache_status_url = instance['apache_status_url']
        except KeyError:
            raise Exception("Missing 'apache_status_url' in Apache config")

        url = self.assumed_url.get(apache_status_url, apache_status_url)
        tags = instance.get('tags', [])

        # Submit a service check for status page availability.
        parsed_url = urlparse(url)
        apache_host = parsed_url.hostname
        apache_port = parsed_url.port or 80
        service_check_name = 'apache.can_connect'
        service_check_tags = ['host:%s' % apache_host, 'port:%s' % apache_port] + tags
        try:
            self.log.debug(
                'apache check initiating request, connect timeout %d receive %d'
                % (self.http.options['timeout'][0], self.http.options['timeout'][1])
            )

            r = self.http.get(url)
            r.raise_for_status()

        except Exception as e:
            self.log.warning("Caught exception %s" % str(e))
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=service_check_tags)
            raise
        else:
            self.service_check(service_check_name, AgentCheck.OK, tags=service_check_tags)
        self.log.debug("apache check succeeded")
        metric_found = False
        # Loop through and extract the numerical values
        for line in r.iter_lines(decode_unicode=True):
            try:
                metric, value = line.split(': ')
                value = float(value)
            except ValueError:
                continue
            # Special case: kBytes => bytes
            if metric == 'Total kBytes':
                value = value * 1024
            # Send metric as a gauge, if applicable
            try:
                self.gauge(self.GAUGES[metric], value, tags=tags)
                metric_found = True
            except KeyError:
                pass
            # Send metric as a rate, if applicable
            try:
                self.rate(self.RATES[metric], value, tags=tags)
                metric_found = True
            except KeyError:
                pass

        if not metric_found:
            if self.assumed_url.get(apache_status_url, None) is None and url[-5:] != '?auto':
                self.assumed_url[apache_status_url] = '%s?auto' % url
                self.warning("Assuming url was not correct. Trying to add ?auto suffix to the url")
                self.check(instance)
            else:
                raise Exception(
                    "No metrics were fetched for this instance. Make sure that %s is the proper url."
                    % apache_status_url
                )
