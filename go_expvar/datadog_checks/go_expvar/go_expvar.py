# (C) Datadog, Inc. 2014-present
# (C) Cory Watson <cory@stripe.com> 2015-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import re
from collections import defaultdict

from six import iteritems
from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck

DEFAULT_MAX_METRICS = 350
PATH = "path"
ALIAS = "alias"
TYPE = "type"
TAGS = "tags"

GAUGE = "gauge"
RATE = "rate"
COUNT = "count"
COUNTER = "counter"  # Deprecated
MONOTONIC_COUNTER = "monotonic_counter"
DEFAULT_TYPE = GAUGE


SUPPORTED_TYPES = {
    GAUGE: AgentCheck.gauge,
    RATE: AgentCheck.rate,
    COUNT: AgentCheck.count,
    COUNTER: AgentCheck.increment,  # Deprecated
    MONOTONIC_COUNTER: AgentCheck.monotonic_count,
}

DEFAULT_METRIC_NAMESPACE = "go_expvar"


# See http://golang.org/pkg/runtime/#MemStats
DEFAULT_GAUGE_MEMSTAT_METRICS = [
    # General statistics
    "Alloc",
    # Main allocation heap statistics
    "HeapAlloc",
    "HeapSys",
    "HeapIdle",
    "HeapInuse",
    "HeapReleased",
    "HeapObjects",
    "TotalAlloc",
]

DEFAULT_RATE_MEMSTAT_METRICS = [
    # General statistics
    "Lookups",
    "Mallocs",
    "Frees",
    # Garbage collector statistics
    "PauseTotalNs",
    "NumGC",
]

DEFAULT_METRICS = (
    [{PATH: "memstats/%s" % path, TYPE: GAUGE} for path in DEFAULT_GAUGE_MEMSTAT_METRICS]
    + [{PATH: "memstats/%s" % path, TYPE: RATE} for path in DEFAULT_RATE_MEMSTAT_METRICS]
)

GO_EXPVAR_URL_PATH = "/debug/vars"


class GoExpvar(AgentCheck):
    HTTP_CONFIG_REMAPPER = {
        'ssl_verify': {'name': 'tls_verify', 'default': None},
        'ssl_certfile': {'name': 'tls_cert', 'default': None},
        'ssl_keyfile': {'name': 'tls_private_key', 'default': None},
    }

    def __init__(self, name, init_config, instances):
        super(GoExpvar, self).__init__(name, init_config, instances)
        self._regexes = {}
        self._last_gc_count = defaultdict(int)

    def _get_data(self, url, instance):
        resp = self.http.get(url)
        resp.raise_for_status()
        return resp.json()

    def _load(self, instance):
        url = instance.get('expvar_url')
        if not url:
            raise Exception('GoExpvar instance missing "expvar_url" value.')

        parsed_url = urlparse(url)
        # if no path is specified we use the default one
        if not parsed_url.path:
            url = parsed_url._replace(path=GO_EXPVAR_URL_PATH).geturl()

        tags = instance.get('tags', [])
        expvar_url_tag = "expvar_url:%s" % url
        if expvar_url_tag not in tags:
            tags.append(expvar_url_tag)

        data = self._get_data(url, instance)
        metrics = DEFAULT_METRICS + instance.get("metrics", [])
        max_metrics = instance.get("max_returned_metrics", DEFAULT_MAX_METRICS)
        namespace = instance.get('namespace', DEFAULT_METRIC_NAMESPACE)
        return data, tags, metrics, max_metrics, url, namespace

    def get_gc_collection_histogram(self, data, tags, url, namespace):
        num_gc = data.get("memstats", {}).get("NumGC")
        pause_hist = data.get("memstats", {}).get("PauseNs")
        last_gc_count = self._last_gc_count[url]
        if last_gc_count == num_gc:
            # No GC has run. Do nothing
            return
        start = last_gc_count % 256
        end = (num_gc + 255) % 256 + 1
        if start < end:
            values = pause_hist[start:end]
        else:
            values = pause_hist[start:] + pause_hist[:end]

        self._last_gc_count[url] = num_gc

        for value in values:
            self.histogram(self.normalize("memstats.PauseNs", namespace, fix_case=True), value, tags=tags)

    def check(self, instance):
        data, tags, metrics, max_metrics, url, namespace = self._load(instance)
        self.get_gc_collection_histogram(data, tags, url, namespace)
        self.parse_expvar_data(data, tags, metrics, max_metrics, namespace)

    def parse_expvar_data(self, data, tags, metrics, max_metrics, namespace):
        '''
        Report all the metrics based on the configuration in instance
        If a metric is not well configured or is not present in the payload,
        continue processing metrics but log the information to the info page
        '''
        count = 0
        for metric in metrics:
            path = metric.get(PATH)
            metric_type = metric.get(TYPE, DEFAULT_TYPE)
            metric_tags = list(metric.get(TAGS, []))
            metric_tags += tags
            alias = metric.get(ALIAS)

            if not path:
                self.warning("Metric %s has no path", metric)
                continue

            if metric_type not in SUPPORTED_TYPES:
                self.warning("Metric type %s not supported for this check", metric_type)
                continue

            keys = path.split("/")
            values = self.deep_get(data, keys)

            if len(values) == 0:
                self.warning("No results matching path %s", path)
                continue

            tag_by_path = alias is not None

            for traversed_path, value in values:
                actual_path = ".".join(traversed_path)
                path_tag = ["path:%s" % actual_path] if tag_by_path else []

                metric_name = alias or self.normalize(actual_path, namespace, fix_case=True)

                try:
                    float(value)
                except (TypeError, ValueError):
                    self.log.warning("Unreportable value for path %s: %s", path, value)
                    continue

                if count >= max_metrics:
                    self.warning(
                        "Reporting more metrics than the allowed maximum. "
                        "Please contact support@datadoghq.com for more information."
                    )
                    return

                SUPPORTED_TYPES[metric_type](self, metric_name, value, metric_tags + path_tag)

                # Submit 'go_expvar.memstats.total_alloc' as a monotonic count
                if metric_name == 'go_expvar.memstats.total_alloc':
                    self.monotonic_count(metric_name + '.count', value, metric_tags + path_tag)
                    count += 1

                count += 1

    def deep_get(self, content, keys, traversed_path=None):
        '''
        Allow to retrieve content nested inside a several layers deep dict/list

        Examples: -content: {
                            "key1": {
                                "key2" : [
                                            {
                                                "name"  : "object1",
                                                "value" : 42
                                            },
                                            {
                                                "name"  : "object2",
                                                "value" : 72
                                            }
                                          ]
                            }
                        }
                  -keys: ["key1", "key2", "1", "value"]
                    would return:
                        [(["key1", "key2", "1", "value"], 72)]
                  -keys: ["key1", "key2", "1", "*"]
                    would return:
                        [(["key1", "key2", "1", "value"], 72), (["key1", "key2", "1", "name"], "object2")]
                  -keys: ["key1", "key2", "*", "value"]
                    would return:
                        [(["key1", "key2", "1", "value"], 72), (["key1", "key2", "0", "value"], 42)]
        '''

        if traversed_path is None:
            traversed_path = []

        if keys == []:
            return [(traversed_path, content)]

        key = keys[0]
        if key.isalnum():
            # key is not a regex, simply match for equality
            matcher = key.__eq__
        else:
            # key might be a regex
            key_regex = self._regexes.get(key)
            if key_regex is None:
                # we don't have it cached, compile it
                regex = "^{}$".format(key)
                try:
                    key_regex = re.compile(regex)
                except Exception:
                    self.warning("Cannot compile regex: %s", regex)
                    return []
                self._regexes[key] = key_regex
            matcher = key_regex.match

        results = []
        for new_key, new_content in self.items(content):
            if matcher(new_key):
                results.extend(self.deep_get(new_content, keys[1:], traversed_path + [str(new_key)]))
        return results

    def items(self, object):
        if isinstance(object, list):
            for new_key, new_content in enumerate(object):
                yield str(new_key), new_content
        elif isinstance(object, dict):
            for new_key, new_content in iteritems(object):
                yield str(new_key), new_content
        else:
            self.log.warning("Could not parse this object, check the json served by the expvar")
