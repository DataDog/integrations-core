# (C) Datadog, Inc. 2016-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import socket

# 3rd party
import simplejson as json

# project
from datadog_checks.checks import AgentCheck

GLOBAL_STATS = set([
    'curr_connections',
])

GLOBAL_STATS_RATES = set([
    'total_connections'
])

POOL_STATS = set([
    'client_connections',
    'server_ejects',
])

POOL_STATS_RATES = set([
    'client_eof',
    'client_err',
    'forward_error',
    'fragments'
])

SERVER_STATS = set([
    'server_connections',
    'server_timedout',
])

SERVER_STATS_RATES = set([
    'in_queue',
    'out_queue',
    'in_queue_bytes',
    'out_queue_bytes',
    'requests',
    'request_bytes',
    'responses',
    'response_bytes',
    'server_err',
    'server_eof'
])


class Twemproxy(AgentCheck):
    """Tracks twemproxy metrics via the stats monitoring port

    Connects to twemproxy via the configured stats port.
    See https://github.com/twitter/twemproxy#observability

    $ curl localhost:22222
    {
        "service":"nutcracker",
        "source":"i-deadbeef",
        "version":"0.4.1",
        "uptime":4018,
        "timestamp":1446677875,
        "total_connections":244,
        "curr_connections":23,
        "poolA": {
            # pool stats
            "client_eof":221,
            "client_err":0,
            "client_connections":15,
            "server_ejects":0,
            "forward_error":0,
            "fragments":0,
            "serverA": {
                # server stats
                "server_eof":0,
                "server_err":0,
                "server_timedout":0,
                "server_connections":1,
                "server_ejected_at":0,
                "requests":46873,
                "request_bytes":127685831,
                "responses":46872,
                "response_bytes":194030,
                "in_queue":1,
                "in_queue_bytes":190,
                "out_queue":0,
                "out_queue_bytes":0
            }
        }
    }

    """

    SERVICE_CHECK_NAME = 'twemproxy.can_connect'

    def check(self, instance):
        if 'host' not in instance:
            raise Exception('Twemproxy instance missing "host" value.')
        tags = instance.get('tags', [])

        response = self._get_data(instance)
        self.log.debug(u"Twemproxy `response`: {0}".format(response))

        if not response:
            self.log.warning(u"No response received from twemproxy.")
            return

        metrics = Twemproxy.parse_json(response, tags)
        for row in metrics:
            try:
                name, value, tags = row
                if name.split('.')[1] in (GLOBAL_STATS | POOL_STATS | SERVER_STATS):
                    self.gauge(name, value, tags)
                else:
                    self.rate(name, value, tags)
            except Exception, e:
                self.log.error(
                    u'Could not submit metric: %s: %s',
                    repr(row), str(e)
                )

    def _get_data(self, instance):
        host = instance.get('host')
        port = int(instance.get('port', 2222))  # 2222 is default
        tags = instance.get('tags', [])
        if tags is None:
            tags = []

        service_check_tags = ['host:{}'.format(host), 'port:{}'.format(port)] + tags
        service_check_tags = list(set(service_check_tags))

        try:
            addrs = socket.getaddrinfo(host, port, 0, 0, socket.IPPROTO_TCP)
        except socket.gaierror as e:
            self.log.warning("unable to retrieve address info for %s:%s - %s", host, port, e)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags)
            return None

        response = ""
        for addr in addrs:
            try:
                if addr[1] == socket.SOCK_STREAM:
                    client = socket.socket(*addr[0:3])
                    client.connect(addr[-1])

                    self.log.debug(u"Querying: {0}:{1}".format(host, port))
                    while 1:
                        data = client.recv(1024)
                        if not data:
                            break
                        response = ''.join([response, data])

                client.close()
                break
            except socket.error as e:
                self.log.warning("unable to connect to %s - %s", addr[-1], e)

        status = AgentCheck.OK if response else AgentCheck.CRITICAL
        self.service_check(self.SERVICE_CHECK_NAME, status, tags=service_check_tags)

        return response

    @classmethod
    def parse_json(cls, raw, tags=None):
        if tags is None:
            tags = []
        parsed = json.loads(raw)
        metric_base = 'twemproxy'
        output = []

        for key, val in parsed.iteritems():
            if isinstance(val, dict):
                # server pool
                pool_tags = tags + ['pool:%s' % key]
                for server_key, server_val in val.iteritems():
                    if isinstance(server_val, dict):
                        # server
                        server_tags = pool_tags + ['server:%s' % server_key]
                        for stat in (SERVER_STATS | SERVER_STATS_RATES):
                            metric_name = '%s.%s' % (metric_base, stat)
                            output.append(
                                (metric_name, server_val.get(stat), server_tags)
                            )

                    elif server_key in (POOL_STATS | POOL_STATS_RATES):
                        metric_name = '%s.%s' % (metric_base, server_key)
                        output.append((metric_name, server_val, pool_tags))

            elif key in (GLOBAL_STATS | GLOBAL_STATS_RATES):
                metric_name = '%s.%s' % (metric_base, key)
                output.append((metric_name, val, tags))

        return output
