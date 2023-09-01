# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

from typing import List, Optional  # noqa: F401

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
        self.hostname = self.instance.get('hostname')  # type: str
        if not self.hostname:
            raise ConfigurationError('A valid "hostname" must be specified')
        self.nameserver = self.instance.get('nameserver')  # type: Optional[str]
        self.timeout = float(
            self.instance.get('timeout', init_config.get('default_timeout', self.DEFAULT_TIMEOUT))
        )  # type: float

        self.record_type = self.instance.get('record_type', 'A')  # type: str
        resolved_as = self.instance.get('resolves_as', '')
        if resolved_as and self.record_type not in ['A', 'CNAME', 'MX']:
            raise ConfigurationError('"resolves_as" can currently only support A, CNAME and MX records')
        self.resolves_as_ips = (
            [x.strip().lower() for x in resolved_as.split(',')] if resolved_as else []
        )  # type: List[str]

        self.base_tags = self.instance.get('tags', []) + [
            'resolved_hostname:{}'.format(self.hostname),
            'instance:{}'.format(self.instance.get('name', self.hostname)),
            'record_type:{}'.format(self.record_type),
        ]
        if resolved_as:
            self.base_tags.append('resolved_as:{}'.format(resolved_as))

    def _get_resolver(self):
        # type: () -> dns.resolver.Resolver
        # Fetches the conf and creates a resolver accordingly
        resolver = dns.resolver.Resolver()  # type: dns.resolver.Resolver

        # If a specific DNS server was defined use it, else use the system default
        nameserver_port = self.instance.get('nameserver_port')  # type: Optional[int]
        if self.nameserver is not None:
            resolver.nameservers = [self.nameserver]
        if nameserver_port is not None:
            resolver.port = nameserver_port

        resolver.lifetime = self.timeout

        return resolver

    def check(self, _):
        resolver = self._get_resolver()

        # Perform the DNS query, and report its duration as a gauge
        t0 = get_precise_time()

        try:
            self.log.debug('Querying "%s" record for hostname "%s"...', self.record_type, self.hostname)
            if self.record_type == "NXDOMAIN":
                try:
                    resolver.query(self.hostname)
                except dns.resolver.NXDOMAIN:
                    pass
                else:
                    raise AssertionError("Expected an NXDOMAIN, got a result.")
            else:
                answer = resolver.query(self.hostname, rdtype=self.record_type)  # dns.resolver.Answer
                assert answer.rrset.items[0].to_text()
                if self.resolves_as_ips:
                    self._check_answer(answer)

            response_time = get_precise_time() - t0

        except dns.exception.Timeout:
            self.log.error('DNS resolution of %s timed out', self.hostname)
            self.report_as_service_check(AgentCheck.CRITICAL, 'DNS resolution of {} timed out'.format(self.hostname))

        except Exception:
            self.log.exception('DNS resolution of %s has failed.', self.hostname)
            self.report_as_service_check(AgentCheck.CRITICAL, 'DNS resolution of {} has failed'.format(self.hostname))

        else:
            tags = self._get_tags()
            if response_time > 0:
                self.gauge('dns.response_time', response_time, tags=tags)
            self.log.debug('Resolved hostname: %s', self.hostname)
            self.report_as_service_check(AgentCheck.OK)

    def _check_answer(self, answer):
        # type: (dns.resolver.Answer) -> None
        number_of_results = len(answer.rrset.items)

        assert len(self.resolves_as_ips) == number_of_results
        result_ips = []
        for rip in answer.rrset.items:
            result = rip.to_text().lower()
            if result.endswith('.'):
                result = result[:-1]
            result_ips.append(result)

        for ip in self.resolves_as_ips:
            assert ip in result_ips

    def _get_tags(self):
        nameserver = ''
        try:
            nameserver = self.nameserver or dns.resolver.Resolver().nameservers[0]
        except IndexError:
            self.log.error('No DNS server was found on this host.')

        return self.base_tags + ['nameserver:{}'.format(nameserver)]

    def report_as_service_check(self, status, msg=None):
        tags = self._get_tags()
        self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags, message=msg)
