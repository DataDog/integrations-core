# stdlib
import urllib2

# 3rd party
import simplejson as json

# project
from checks import AgentCheck

GLOBAL_STATS = set([
    'curr_connections',
    'total_connections'
])

POOL_STATS = set([
    'client_eof',
    'client_err',
    'client_connections',
    'server_ejects',
    'forward_error'
])

SERVER_STATS = set([
    'in_queue',
    'out_queue',
    'server_connections',
    'server_err',
    'server_timedout',
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
    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Twemproxy instance missing "url" value.')
        tags = instance.get('tags', [])

        response = self._get_data(instance)
        self.log.debug(u"Nginx status `response`: {0}".format(response))

        metrics = self.parse_json(response, tags)
        for row in metrics:
            try:
                name, value, tags = row
                self.gauge(name, value, tags)
            except Exception, e:
                self.log.error(
                    u'Could not submit metric: %s: %s',
                    (repr(row), str(e))
                )

    def _get_data(self, instance):
        url = instance.get('url')

        self.log.debug(u"Querying URL: {0}".format(url))
        response = urllib2.urlopen(url)
        return response.read()

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
                for pool_key, pool_val in val.iteritems():
                    if isinstance(pool_val, dict):
                        # server
                        server_tags = pool_tags + ['server:%s' % pool_key]
                        for stat in SERVER_STATS:
                            metric_name = '%s.%s' % (metric_base, stat)
                            output.append(
                                (metric_name, pool_val.get(stat), server_tags)
                            )

                    elif pool_key in POOL_STATS:
                        metric_name = '%s.%s' % (metric_base, pool_key)
                        output.append((metric_name, pool_val, pool_tags))

            elif key in GLOBAL_STATS:
                metric_name = '%s.%s' % (metric_base, key)
                output.append((metric_name, val, tags))

        return output
