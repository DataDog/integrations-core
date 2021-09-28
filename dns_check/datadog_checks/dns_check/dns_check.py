# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import dns.resolver

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.time import get_precise_time


class DNSCheck(AgentCheck):
    SERVICE_CHECK_NAME = 'dns.can_resolve'
    DEFAULT_TIMEOUT = 5

    def __init__(self, name, init_config, instances):
        inst = instances[0]
        inst.setdefault("name", "dns-check-0")

        super(DNSCheck, self).__init__(name, init_config, instances)

        self.default_timeout = init_config.get('default_timeout', self.DEFAULT_TIMEOUT)

    def _load_conf(self):
        # Fetches the conf
        hostname = self.instance.get('hostname')
        if not hostname:
            raise ConfigurationError('A valid "hostname" must be specified')

        resolver = dns.resolver.Resolver()

        # If a specific DNS server was defined use it, else use the system default
        nameserver = self.instance.get('nameserver')
        nameserver_port = self.instance.get('nameserver_port')
        if nameserver is not None:
            resolver.nameservers = [nameserver]
        if nameserver_port is not None:
            resolver.port = nameserver_port

        timeout = float(self.instance.get('timeout', self.default_timeout))
        resolver.lifetime = timeout
        record_type = self.instance.get('record_type', 'A')
        resolves_as = self.instance.get('resolves_as', None)
        if resolves_as and record_type not in ['A', 'CNAME', 'MX']:
            raise ConfigurationError('"resolves_as" can currently only support A, CNAME and MX records')

        return hostname, timeout, nameserver, record_type, resolver, resolves_as

    def check(self, _):
        hostname, timeout, nameserver, record_type, resolver, resolves_as = self._load_conf()

        # Perform the DNS query, and report its duration as a gauge
        t0 = get_precise_time()

        try:
            self.log.debug('Querying "%s" record for hostname "%s"...', record_type, hostname)
            if record_type == "NXDOMAIN":
                try:
                    resolver.query(hostname)
                except dns.resolver.NXDOMAIN:
                    pass
                else:
                    raise AssertionError("Expected an NXDOMAIN, got a result.")
            else:
                answer = resolver.query(hostname, rdtype=record_type)
                assert answer.rrset.items[0].to_text()
                if resolves_as:
                    self._check_answer(answer, resolves_as)

            response_time = get_precise_time() - t0

        except dns.exception.Timeout:
            self.log.error('DNS resolution of %s timed out', hostname)
            self.report_as_service_check(AgentCheck.CRITICAL, 'DNS resolution of {} timed out'.format(hostname))

        except Exception:
            self.log.exception('DNS resolution of %s has failed.', hostname)
            self.report_as_service_check(AgentCheck.CRITICAL, 'DNS resolution of {} has failed'.format(hostname))

        else:
            tags = self._get_tags()
            if response_time > 0:
                self.gauge('dns.response_time', response_time, tags=tags)
            self.log.debug('Resolved hostname: %s', hostname)
            self.report_as_service_check(AgentCheck.OK)

    def _check_answer(self, answer, resolves_as):
        ips = [x.strip().lower() for x in resolves_as.split(',')]
        number_of_results = len(answer.rrset.items)

        assert len(ips) == number_of_results
        result_ips = []
        for rip in answer.rrset.items:
            result = rip.to_text().lower()
            if result.endswith('.'):
                result = result[:-1]
            result_ips.append(result)

        for ip in ips:
            assert ip in result_ips

    def _get_tags(self):
        hostname = self.instance.get('hostname')
        instance_name = self.instance.get('name', hostname)
        record_type = self.instance.get('record_type', 'A')
        custom_tags = self.instance.get('tags', [])
        resolved_as = self.instance.get('resolves_as')

        nameserver = ''
        try:
            nameserver = self.instance.get('nameserver') or dns.resolver.Resolver().nameservers[0]
        except IndexError:
            self.log.error('No DNS server was found on this host.')

        tags = custom_tags + [
            'nameserver:{}'.format(nameserver),
            'resolved_hostname:{}'.format(hostname),
            'instance:{}'.format(instance_name),
            'record_type:{}'.format(record_type),
        ]
        if resolved_as:
            tags.append('resolved_as:{}'.format(resolved_as))

        return tags

    def report_as_service_check(self, status, msg=None):
        tags = self._get_tags()
        self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags, message=msg)
