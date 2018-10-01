# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import time
import dns.resolver

from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.checks import NetworkCheck, Status

# These imports are necessary because otherwise dynamic type
# resolution will fail on windows without it.
# See more here: https://github.com/rthalley/dnspython/issues/39.
if Platform.is_win32():
    from dns.rdtypes.ANY import *  # noqa
    from dns.rdtypes.IN import *  # noqa
    # for tiny time deltas, time.time on Windows reports the same value
    # of the clock more than once, causing the computation of response_time
    # to be often 0; let's use time.clock that is more precise.
    time_func = time.clock
else:
    time_func = time.time


class BadConfException(Exception):
    pass


class DNSCheck(NetworkCheck):
    SERVICE_CHECK_NAME = 'dns.can_resolve'
    DEFAULT_TIMEOUT = 5

    def __init__(self, name, init_config, agentConfig, instances=None):
        # Now that the DNS check is a Network check, we must provide a `name` for each
        # instance before calling NetworkCheck to make backwards compatible with old yaml.
        if instances is not None:
            for idx, inst in enumerate(instances):
                try:
                    inst['name'] = inst['name']
                except KeyError:
                    inst['name'] = "dns-check-{}".format(idx)

        NetworkCheck.__init__(self, name, init_config, agentConfig, instances)

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

        return hostname, timeout, nameserver, record_type, resolver

    def _check(self, instance):
        hostname, timeout, nameserver, record_type, resolver = self._load_conf(instance)

        # Perform the DNS query, and report its duration as a gauge
        response_time = 0
        t0 = time_func()

        try:
            self.log.debug('Querying "{0}" record for hostname "{1}"...'.format(record_type, hostname))
            if record_type == "NXDOMAIN":
                try:
                    resolver.query(hostname)
                except dns.resolver.NXDOMAIN:
                    pass
                else:
                    raise AssertionError("Expected an NXDOMAIN, got a result.")
            else:
                answer = resolver.query(hostname, rdtype=record_type)
                assert(answer.rrset.items[0].to_text())

            response_time = time_func() - t0

        except dns.exception.Timeout:
            self.log.error('DNS resolution of {0} timed out'.format(hostname))
            return Status.CRITICAL, 'DNS resolution of {0} timed out'.format(hostname)

        except Exception:
            self.log.exception('DNS resolution of {0} has failed.'.format(hostname))
            return Status.CRITICAL, 'DNS resolution of {0} has failed'.format(hostname)

        else:
            tags = self._get_tags(instance)
            if response_time > 0:
                self.gauge('dns.response_time', response_time, tags=tags)
            self.log.debug('Resolved hostname: {0}'.format(hostname))
            return Status.UP, 'UP'

    def _get_tags(self, instance):
        hostname = instance.get('hostname')
        instance_name = instance.get('name', hostname)
        record_type = instance.get('record_type', 'A')
        custom_tags = instance.get('tags', [])
        tags = []

        try:
            nameserver = instance.get('nameserver') or dns.resolver.Resolver().nameservers[0]
            tags.append('nameserver:{0}'.format(nameserver))
        except IndexError:
            self.log.error('No DNS server was found on this host.')

        tags = custom_tags + ['nameserver:{0}'.format(nameserver),
                              'resolved_hostname:{0}'.format(hostname),
                              'instance:{0}'.format(instance_name),
                              'record_type:{0}'.format(record_type)]
        return tags

    def report_as_service_check(self, sc_name, status, instance, msg=None):
        tags = self._get_tags(instance)

        if status == Status.UP:
            msg = None

        self.service_check(self.SERVICE_CHECK_NAME,
                           NetworkCheck.STATUS_TO_SERVICE_CHECK[status],
                           tags=tags,
                           message=msg
                           )
