# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import time

import dns.resolver
from six import PY3

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.platform import Platform

if PY3:
    # use higher precision clock available in Python3
    time_func = time.perf_counter
elif Platform.is_win32():
    # for tiny time deltas, time.time on Windows reports the same value
    # of the clock more than once, causing the computation of response_time
    # to be often 0; let's use time.clock that is more precise.
    time_func = time.clock
else:
    time_func = time.time


class BadConfException(Exception):
    pass


class DNSCheck(AgentCheck):
    SERVICE_CHECK_NAME = 'dns.can_resolve'
    DEFAULT_TIMEOUT = 5

    def __init__(self, name, init_config, instances):
        inst = instances[0]
        inst.setdefault("name", "dns-check-0")

        super(DNSCheck, self).__init__(name, init_config, instances)

        self.default_timeout = init_config.get('default_timeout', self.DEFAULT_TIMEOUT)

    def _load_conf(self, instance):
        # Fetches the conf
        hostname = instance.get('hostname')
        if not hostname:
            raise BadConfException('A valid "hostname" must be specified')

        resolver = dns.resolver.Resolver()

        # If a specific DNS server was defined use it, else use the system default
        nameserver = instance.get('nameserver')
        nameserver_port = instance.get('nameserver_port')
        if nameserver is not None:
            resolver.nameservers = [nameserver]
        if nameserver_port is not None:
            resolver.port = nameserver_port

        timeout = float(instance.get('timeout', self.default_timeout))
        resolver.lifetime = timeout
        record_type = instance.get('record_type', 'A')
        resolves_as = instance.get('resolves_as', None)
        if resolves_as and record_type not in ['A', 'CNAME', 'MX']:
            raise BadConfException('"resolves_as" can currently only support A, CNAME and MX records')

        return hostname, timeout, nameserver, record_type, resolver, resolves_as

    def check(self, instance):
        hostname, timeout, nameserver, record_type, resolver, resolves_as = self._load_conf(instance)

        # Perform the DNS query, and report its duration as a gauge
        t0 = time_func()

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

            response_time = time_func() - t0

        except dns.exception.Timeout:
            self.log.error('DNS resolution of %s timed out', hostname)
            self.report_as_service_check(
                AgentCheck.CRITICAL, instance, 'DNS resolution of {} timed out'.format(hostname)
            )

        except Exception:
            self.log.exception('DNS resolution of %s has failed.', hostname)
            self.report_as_service_check(
                AgentCheck.CRITICAL, instance, 'DNS resolution of {} has failed'.format(hostname)
            )

        else:
            tags = self._get_tags(instance)
            if response_time > 0:
                self.gauge('dns.response_time', response_time, tags=tags)
            self.log.debug('Resolved hostname: %s', hostname)
            self.report_as_service_check(AgentCheck.OK, instance)

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

    def _get_tags(self, instance):
        hostname = instance.get('hostname')
        instance_name = instance.get('name', hostname)
        record_type = instance.get('record_type', 'A')
        custom_tags = instance.get('tags', [])
        resolved_as = instance.get('resolves_as')
        tags = []

        try:
            nameserver = instance.get('nameserver') or dns.resolver.Resolver().nameservers[0]
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

    def report_as_service_check(self, status, instance, msg=None):
        tags = self._get_tags(instance)
        self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags, message=msg)
