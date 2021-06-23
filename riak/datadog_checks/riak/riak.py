# (C) Datadog, Inc. 2013-present
# (C) Stefan Mees <stefan.mees@wooga.net> 2013
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import unicodedata
from copy import copy

import simplejson as json

from datadog_checks.base import AgentCheck

from .keys import KEYS, SEARCH_LATENCY_KEYS, STAT_KEYS, VNODEQ_KEYS


class Riak(AgentCheck):
    SERVICE_CHECK_NAME = 'riak.can_connect'

    HTTP_CONFIG_REMAPPER = {
        'cacert': {'name': 'tls_ca_cert'},
        'disable_cert_verify': {'name': 'tls_verify', 'invert': True, 'default': False},
    }

    def __init__(self, name, init_config, instances=None):
        super(Riak, self).__init__(name, init_config, instances)
        self.keys = copy(KEYS)
        for k in ["mean", "median", "95", "99", "100"]:
            for m in STAT_KEYS:
                self.keys.append(m + "_" + k)

        for k in ["min", "max", "mean", "median", "95", "99", "999"]:
            for m in SEARCH_LATENCY_KEYS:
                self.keys.append(m + "_" + k)

        for k in ["min", "max", "mean", "median", "total"]:
            for m in VNODEQ_KEYS:
                self.keys.append(m + "_" + k)

        self.prev_coord_redirs_total = -1
        self.url = self.instance['url']
        default_timeout = float(self.init_config.get('default_timeout', 5))
        self.timeout = float(self.instance.get('timeout', default_timeout))
        self.cacert = self.instance.get('cacert', None)
        self.disable_cert_verify = self.instance.get('disable_cert_verify', False)
        self.tags = self.instance.get('tags', [])
        self.service_check_tags = self.tags + ['url:%s' % self.url]

    def check(self, _):
        try:
            r = self.http.get(self.url)
            r.raise_for_status()
            stats = json.loads(r.content)
        except Exception as e:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message="Unable to fetch Riak stats: %s" % str(e),
                tags=self.service_check_tags,
            )
            raise

        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.service_check_tags)

        for k in self.keys:
            if k in stats:
                self.safe_submit_metric("riak." + k, stats[k], tags=self.tags)

        coord_redirs_total = stats["coord_redirs_total"]
        if self.prev_coord_redirs_total > -1:
            count = coord_redirs_total - self.prev_coord_redirs_total
            self.gauge('riak.coord_redirs', count)

        self.prev_coord_redirs_total = coord_redirs_total

    def safe_submit_metric(self, name, value, tags=None):
        tags = [] if tags is None else tags
        try:
            self.gauge(name, float(value), tags=tags)
            return
        except ValueError:
            self.log.debug("metric name %s cannot be converted to a float: %s", name, value)
            pass

        try:
            self.gauge(name, unicodedata.numeric(value), tags=tags)
            return
        except (TypeError, ValueError):
            self.log.debug("metric name %s cannot be converted to a float even using unicode tools: %s", name, value)
            pass
