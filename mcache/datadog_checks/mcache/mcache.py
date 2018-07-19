# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import bmemcached
import pkg_resources

from datadog_checks.errors import CheckException
from datadog_checks.checks import AgentCheck


class BadResponseError(CheckException):
    pass


class InvalidConfigError(CheckException):
    pass


class Memcache(AgentCheck):

    SOURCE_TYPE_NAME = 'memcached'

    DEFAULT_PORT = 11211

    GAUGES = [
        "total_items",
        "curr_items",
        "limit_maxbytes",
        "uptime",
        "bytes",
        "curr_connections",
        "connection_structures",
        "threads",
        "pointer_size"
    ]

    RATES = [
        "rusage_user",
        "rusage_system",
        "cmd_get",
        "cmd_set",
        "cmd_flush",
        "get_hits",
        "get_misses",
        "delete_misses",
        "delete_hits",
        "evictions",
        "bytes_read",
        "bytes_written",
        "cas_misses",
        "cas_hits",
        "cas_badval",
        "total_connections",
        "listen_disabled_num"
    ]

    ITEMS_RATES = [
        "evicted",
        "evicted_nonzero",
        "expired_unfetched",
        "evicted_unfetched",
        "outofmemory",
        "tailrepairs",
        "moves_to_cold",
        "moves_to_warm",
        "moves_within_lru",
        "reclaimed",
        "crawler_reclaimed",
        "lrutail_reflocked",
        "direct_reclaims",
    ]

    ITEMS_GAUGES = [
        "number",
        "number_hot",
        "number_warm",
        "number_cold",
        "number_noexp",
        "age",
        "evicted_time",
    ]

    SLABS_RATES = [
        "get_hits",
        "cmd_set",
        "delete_hits",
        "incr_hits",
        "decr_hits",
        "cas_hits",
        "cas_badval",
        "touch_hits",
        "used_chunks",
    ]

    SLABS_GAUGES = [
        "chunk_size",
        "chunks_per_page",
        "total_pages",
        "total_chunks",
        "used_chunks",
        "free_chunks",
        "free_chunks_end",
        "mem_requested",
        "active_slabs",
        "total_malloced",
    ]

    # format - "key": (rates, gauges, handler)
    OPTIONAL_STATS = {
        "items": [ITEMS_RATES, ITEMS_GAUGES, None],
        "slabs": [SLABS_RATES, SLABS_GAUGES, None],
    }

    SERVICE_CHECK = 'memcache.can_connect'

    def get_library_versions(self):
        return {
            "memcache": pkg_resources.get_distribution("python-binary-memcached").version
        }

    def _process_response(self, response):
        """
        Examine the response and raise an error is something is off
        """
        if len(response) != 1:
            raise BadResponseError("Malformed response: {}".format(response))

        stats = response.values()[0]
        if not len(stats):
            raise BadResponseError("Malformed response for host: {}".format(stats))

        return stats

    def _get_metrics(self, client, tags, service_check_tags=None):
        try:
            stats = self._process_response(client.stats())
            for metric in stats:
                # Check if metric is a gauge or rate
                if metric in self.GAUGES:
                    our_metric = self.normalize(metric.lower(), 'memcache')
                    self.gauge(our_metric, float(stats[metric]), tags=tags)

                # Tweak the name if it's a rate so that we don't use the exact
                # same metric name as the memcache documentation
                if metric in self.RATES:
                    our_metric = self.normalize(
                        "{0}_rate".format(metric.lower()), 'memcache')
                    self.rate(our_metric, float(stats[metric]), tags=tags)

            # calculate some metrics based on other metrics.
            # stats should be present, but wrap in try/except
            # and log an exception just in case.
            try:
                self.gauge(
                    "memcache.get_hit_percent",
                    100.0 * float(stats["get_hits"]) / float(stats["cmd_get"]),
                    tags=tags,
                )
            except ZeroDivisionError:
                pass

            try:
                self.gauge(
                    "memcache.fill_percent",
                    100.0 * float(stats["bytes"]) / float(stats["limit_maxbytes"]),
                    tags=tags,
                )
            except ZeroDivisionError:
                pass

            try:
                self.gauge(
                    "memcache.avg_item_size",
                    float(stats["bytes"]) / float(stats["curr_items"]),
                    tags=tags,
                )
            except ZeroDivisionError:
                pass

            uptime = stats.get("uptime", 0)
            self.service_check(
                self.SERVICE_CHECK, AgentCheck.OK,
                tags=service_check_tags,
                message="Server has been up for %s seconds" % uptime)
        except BadResponseError:
            raise

    def _get_optional_metrics(self, client, tags, options=None):
        for arg, metrics_args in self.OPTIONAL_STATS.iteritems():
            if not options or options.get(arg, False):
                try:
                    optional_rates = metrics_args[0]
                    optional_gauges = metrics_args[1]
                    optional_fn = metrics_args[2]

                    stats = self._process_response(client.stats(arg))
                    prefix = "memcache.{}".format(arg)

                    for metric, val in stats.iteritems():
                        # Check if metric is a gauge or rate
                        metric_tags = []
                        if optional_fn:
                            metric, metric_tags, val = optional_fn(metric, val)

                        if optional_gauges and metric in optional_gauges:
                            our_metric = self.normalize(metric.lower(), prefix)
                            self.gauge(our_metric, float(val), tags=tags+metric_tags)

                        if optional_rates and metric in optional_rates:
                            our_metric = self.normalize(
                                "{0}_rate".format(metric.lower()), prefix)
                            self.rate(our_metric, float(val), tags=tags+metric_tags)
                except BadResponseError:
                    self.log.warning(
                        "Unable to retrieve optional stats from memcache instance, "
                        "running 'stats %s' they could be empty or bad configuration.", arg
                    )
                except Exception as e:
                    self.log.exception(
                        "Unable to retrieve optional stats from memcache instance: {}".format(e)
                    )

    @staticmethod
    def get_items_stats(key, value):
        """
        Optional metric handler for 'items' stats

        key: "items:<slab_id>:<metric_name>" format
        value: return untouched

        Like all optional metric handlers returns metric, tags, value
        """
        itemized_key = key.split(':')
        slab_id = itemized_key[1]
        metric = itemized_key[2]

        tags = ["slab:{}".format(slab_id)]

        return metric, tags, value

    @staticmethod
    def get_slabs_stats(key, value):
        """
        Optional metric handler for 'items' stats

        key: "items:<slab_id>:<metric_name>" format
        value: return untouched

        Like all optional metric handlers returns metric, tags, value
        """
        slabbed_key = key.split(':')
        tags = []
        if len(slabbed_key) == 2:
            slab_id = slabbed_key[0]
            metric = slabbed_key[1]
            tags = ["slab:{}".format(slab_id)]
        else:
            metric = slabbed_key[0]

        return metric, tags, value

    def check(self, instance):
        socket = instance.get('socket')
        server = instance.get('url')
        options = instance.get('options', {})
        username = instance.get('username')
        password = instance.get('password')

        if not server and not socket:
            raise InvalidConfigError('Either "url" or "socket" must be configured')

        if socket:
            server = 'unix'
            port = socket
            connection_server = "{}".format(port)
        else:
            port = int(instance.get('port', self.DEFAULT_PORT))
            connection_server = "{}:{}".format(server, port)
        custom_tags = instance.get('tags') or []

        mc = None  # client
        tags = ["url:{0}:{1}".format(server, port)] + custom_tags
        service_check_tags = ["host:%s" % server, "port:%s" % port] + custom_tags

        try:
            self.log.debug("Connecting to %s, tags:%s", connection_server, tags)
            mc = bmemcached.Client(connection_server, username, password)

            self._get_metrics(mc, tags, service_check_tags)
            if options:
                # setting specific handlers
                self.OPTIONAL_STATS["items"][2] = Memcache.get_items_stats
                self.OPTIONAL_STATS["slabs"][2] = Memcache.get_slabs_stats
                self._get_optional_metrics(mc, tags, options)
        except BadResponseError as e:
            self.service_check(
                self.SERVICE_CHECK, AgentCheck.CRITICAL,
                tags=service_check_tags,
                message="Unable to fetch stats from server")
            raise CheckException(
                "Unable to retrieve stats from memcache instance: {}:{}."
                "Please check your configuration. ({})".format(server, port, e))

        if mc is not None:
            mc.disconnect_all()
            self.log.debug("Disconnected from memcached")
        del mc
