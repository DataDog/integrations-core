# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from collections import namedtuple

from datadog_checks.base import AgentCheck


class PowerDNSRecursorCheck(AgentCheck):
    # See https://doc.powerdns.com/md/recursor/stats/ for metrics explanation
    GAUGE_METRICS = [
        'cache-entries',
        'concurrent-queries',
        'failed-host-entries',
        'negcache-entries',
        'packetcache-entries',
        'throttle-entries',
    ]
    RATE_METRICS = [
        'all-outqueries',
        'answers-slow',
        'answers0-1',
        'answers1-10',
        'answers10-100',
        'answers100-1000',
        'cache-hits',
        'cache-misses',
        'chain-resends',
        'case-mismatches',
        'client-parse-errors',
        'dont-outqueries',
        'ipv6-outqueries',
        'ipv6-questions',
        'malloc-bytes',
        'noerror-answers',
        'nxdomain-answers',
        'max-mthread-stack',
        'outgoing-timeouts',
        'over-capacity-drops',
        'packetcache-hits',
        'packetcache-misses',
        'policy-drops',
        'qa-latency',
        'questions',
        'server-parse-errors',
        'servfail-answers',
        'spoof-prevents',
        'sys-msec',
        'tcp-client-overflow',
        'tcp-clients',
        'tcp-outqueries',
        'tcp-questions',
        'throttled-out',
        'throttled-outqueries',
        'unauthorized-tcp',
        'unauthorized-udp',
        'unexpected-packets',
        'unreachables',
    ]
    GAUGE_METRICS_V4 = ['fd-usage']
    RATE_METRICS_V4 = [
        'auth4-answers-slow',
        'auth4-answers0-1',
        'auth4-answers1-10',
        'auth4-answers10-100',
        'auth4-answers100-1000',
        'auth6-answers-slow',
        'auth6-answers0-1',
        'auth6-answers1-10',
        'auth6-answers10-100',
        'auth6-answers100-1000',
        'dlg-only-drops',
        'dnssec-queries',
        'dnssec-result-bogus',
        'dnssec-result-indeterminate',
        'dnssec-result-insecure',
        'dnssec-result-nta',
        'dnssec-result-secure',
        'dnssec-validations',
        'edns-ping-matches',
        'edns-ping-mismatches',
        'ignored-packets',
        'no-packet-error',
        'noedns-outqueries',
        'noping-outqueries',
        'nsset-invalidations',
        'nsspeeds-entries',
        'outgoing4-timeouts',
        'outgoing6-timeouts',
        'policy-result-custom',
        'policy-result-drop',
        'policy-result-noaction',
        'policy-result-nodata',
        'policy-result-nxdomain',
        'policy-result-truncate',
        'real-memory-usage',
        'resource-limits',
        'too-old-drops',
        'udp-in-errors',
        'udp-noport-errors',
        'udp-recvbuf-errors',
        'udp-sndbuf-errors',
        'uptime',
        'user-msec',
    ]

    SERVICE_CHECK_NAME = 'powerdns.recursor.can_connect'

    def __init__(self, name, init_config, instances):
        super(PowerDNSRecursorCheck, self).__init__(name, init_config, instances)
        if 'api_key' in self.instance:
            self.http.options['headers']['X-API-Key'] = self.instance['api_key']

    def check(self, instance):
        config, tags = self._get_config(instance)
        stats = self._get_pdns_stats(config, tags)
        for stat in stats:
            if stat['name'] in PowerDNSRecursorCheck.GAUGE_METRICS:
                self.gauge('powerdns.recursor.{}'.format(stat['name']), float(stat['value']), tags=tags)
            elif stat['name'] in PowerDNSRecursorCheck.RATE_METRICS:
                self.rate('powerdns.recursor.{}'.format(stat['name']), float(stat['value']), tags=tags)

            # collect additional version 4 statistics.
            if config.version == 4:
                if stat['name'] in PowerDNSRecursorCheck.GAUGE_METRICS_V4:
                    self.gauge('powerdns.recursor.{}'.format(stat['name']), float(stat['value']), tags=tags)
                elif stat['name'] in PowerDNSRecursorCheck.RATE_METRICS_V4:
                    self.rate('powerdns.recursor.{}'.format(stat['name']), float(stat['value']), tags=tags)

        self._collect_metadata(config)

    def _get_config(self, instance):
        required = ['host', 'port']
        for param in required:
            if not instance.get(param):
                raise Exception("powerdns_recursor instance missing %s. Skipping." % (param))

        host = instance.get('host')
        port = int(instance.get('port'))
        version = instance.get('version')
        tags = instance.get('tags', [])
        if tags is None:
            tags = []
        Config = namedtuple('Config', ['host', 'port', 'version'])

        return Config(host, port, version), tags

    def _get_pdns_stats(self, config, tags):
        url_v4 = "http://{}:{}/api/v1/servers/localhost/statistics".format(config.host, config.port)
        url = "http://{}:{}/servers/localhost/statistics".format(config.host, config.port)

        service_check_tags = ['recursor_host:{}'.format(config.host), 'recursor_port:{}'.format(config.port)] + tags

        try:
            request = self._get_pdns_response(config, url, url_v4)
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags)
            raise

        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)
        return request.json()

    def _get_pdns_response(self, config, url, url_v4):
        if config.version == 4:
            url = url_v4

        try:
            response = self.http.get(url)
            response.raise_for_status()
        except Exception:
            if url_v4 is url:
                raise
            response = self.http.get(url_v4)
            response.raise_for_status()

        return response

    @AgentCheck.metadata_entrypoint
    def _collect_metadata(self, config):
        url_v4 = "http://{}:{}/api".format(config.host, config.port)
        url = "http://{}:{}/servers/localhost/statistics".format(config.host, config.port)

        try:
            response = self._get_pdns_response(config, url, url_v4)
        except Exception as e:
            self.log.debug('Error collecting PowerDNS Recursor version: %s', str(e))
            return

        if response.headers.get('Server'):
            try:
                # 'Server': 'PowerDNS/4.0.9'
                version = response.headers['Server'].split('/')[1]
                self.set_metadata('version', version)
            except Exception as e:
                self.log.debug('Error while decoding PowerDNS Recursor version: %s', str(e))
        else:
            self.log.debug("Couldn't find the PowerDNS Recursor Server version header")
