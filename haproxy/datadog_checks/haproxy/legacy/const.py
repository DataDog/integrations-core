# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

from datadog_checks.base import AgentCheck

STATS_URL = "/;csv;norefresh"
EVENT_TYPE = SOURCE_TYPE_NAME = 'haproxy'
BUFSIZE = 8192
UPTIME_PARSER = re.compile(r"(?P<days>\d+)d (?P<hours>\d+)h(?P<minutes>\d+)m(?P<seconds>\d+)s")


class Services(object):
    BACKEND = 'BACKEND'
    FRONTEND = 'FRONTEND'
    ALL = (BACKEND, FRONTEND)

    # Statuses that we normalize to and that are reported by
    # `haproxy.count_per_status` by default (unless `collate_status_tags_per_host` is enabled)
    ALL_STATUSES = ('up', 'open', 'down', 'maint', 'nolb')

    AVAILABLE = 'available'
    UNAVAILABLE = 'unavailable'
    COLLATED_STATUSES = (AVAILABLE, UNAVAILABLE)

    BACKEND_STATUS_TO_COLLATED = {'up': AVAILABLE, 'down': UNAVAILABLE, 'maint': UNAVAILABLE, 'nolb': UNAVAILABLE}

    STATUS_TO_COLLATED = {
        'up': AVAILABLE,
        'open': AVAILABLE,
        'down': UNAVAILABLE,
        'maint': UNAVAILABLE,
        'nolb': UNAVAILABLE,
    }

    STATUS_TO_SERVICE_CHECK = {
        'up': AgentCheck.OK,
        'down': AgentCheck.CRITICAL,
        'no_check': AgentCheck.UNKNOWN,
        'maint': AgentCheck.OK,
    }


METRICS = {
    "qcur": ("gauge", "queue.current"),
    "scur": ("gauge", "session.current"),
    "slim": ("gauge", "session.limit"),
    "spct": ("gauge", "session.pct"),  # Calculated as: (scur/slim)*100
    "stot": ("rate", "session.rate"),
    "bin": [("rate", "bytes.in_rate"), ("gauge", "bytes.in.total")],
    "bout": [("rate", "bytes.out_rate"), ("gauge", "bytes.out.total")],
    "dreq": ("rate", "denied.req_rate"),
    "dresp": ("rate", "denied.resp_rate"),
    "ereq": ("rate", "errors.req_rate"),
    "econ": ("rate", "errors.con_rate"),
    "eresp": ("rate", "errors.resp_rate"),
    "wretr": ("rate", "warnings.retr_rate"),
    "wredis": ("rate", "warnings.redis_rate"),
    "lastchg": ("gauge", "uptime"),
    "req_rate": ("gauge", "requests.rate"),  # HA Proxy 1.4 and higher
    "req_tot": ("rate", "requests.tot_rate"),  # HA Proxy 1.4 and higher
    "hrsp_1xx": ("rate", "response.1xx"),  # HA Proxy 1.4 and higher
    "hrsp_2xx": ("rate", "response.2xx"),  # HA Proxy 1.4 and higher
    "hrsp_3xx": ("rate", "response.3xx"),  # HA Proxy 1.4 and higher
    "hrsp_4xx": ("rate", "response.4xx"),  # HA Proxy 1.4 and higher
    "hrsp_5xx": ("rate", "response.5xx"),  # HA Proxy 1.4 and higher
    "hrsp_other": ("rate", "response.other"),  # HA Proxy 1.4 and higher
    "qtime": ("gauge", "queue.time"),  # HA Proxy 1.5 and higher
    "ctime": ("gauge", "connect.time"),  # HA Proxy 1.5 and higher
    "rtime": ("gauge", "response.time"),  # HA Proxy 1.5 and higher
    "ttime": ("gauge", "session.time"),  # HA Proxy 1.5 and higher
    "conn_rate": ("gauge", "connections.rate"),  # HA Proxy 1.7 and higher
    "conn_tot": ("rate", "connections.tot_rate"),  # HA Proxy 1.7 and higher
    "intercepted": ("rate", "requests.intercepted"),  # HA Proxy 1.7 and higher
}
