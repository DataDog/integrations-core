import os

import pytest

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.dev.utils import ON_LINUX, ON_MACOS

AGG_STATUSES_BY_SERVICE = (
    (['status:available', 'service:a', 'haproxy_service:a'], 1),
    (['status:available', 'service:b', 'haproxy_service:b'], 4),
    (['status:unavailable', 'service:b', 'haproxy_service:b'], 2),
    (
        [
            'status:available',
            'service:be_edge_http_sre-production_elk-kibana',
            'haproxy_service:be_edge_http_sre-production_elk-kibana',
        ],
        1,
    ),
    (
        [
            'status:unavailable',
            'service:be_edge_http_sre-production_elk-kibana',
            'haproxy_service:be_edge_http_sre-production_elk-kibana',
        ],
        2,
    ),
)

AGG_STATUSES_BY_SERVICE_DISABLE_SERVICE_TAG = (
    (['status:available', 'haproxy_service:a'], 1),
    (['status:available', 'haproxy_service:b'], 4),
    (['status:unavailable', 'haproxy_service:b'], 2),
    (['status:available', 'haproxy_service:be_edge_http_sre-production_elk-kibana'], 1),
    (['status:unavailable', 'haproxy_service:be_edge_http_sre-production_elk-kibana'], 2),
)

AGG_STATUSES = ((['status:available'], 6), (['status:unavailable'], 4))

CHECK_NAME = 'haproxy'
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
HOST = get_docker_hostname()
SOCKET_PORT = '13834'
PORT = '13835'
PORT_OPEN = '13836'
BASE_URL = "http://{0}:{1}".format(HOST, PORT)
BASE_URL_OPEN = "http://{0}:{1}".format(HOST, PORT_OPEN)
STATS_URL = "{0}/stats".format(BASE_URL)
STATS_URL_OPEN = "{0}/stats".format(BASE_URL_OPEN)
STATS_SOCKET = "tcp://{0}:{1}".format(HOST, SOCKET_PORT)
USERNAME = 'datadog'
PASSWORD = 'isdevops'
HAPROXY_VERSION = os.getenv('HAPROXY_VERSION')

platform_supports_sockets = ON_LINUX or ON_MACOS
platform_supports_sharing_unix_sockets_through_docker = ON_LINUX
requires_socket_support = pytest.mark.skipif(
    not platform_supports_sockets, reason='Windows sockets are not file handles'
)
requires_shareable_unix_socket = pytest.mark.skipif(
    not platform_supports_sharing_unix_sockets_through_docker,
    reason='AF_UNIX sockets cannot be bind-mounted between a macOS host and a linux guest in docker',
)
haproxy_less_than_1_7 = os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2] < ['1', '7']

CONFIG_UNIXSOCKET = {'collect_aggregates_only': False}


CONFIG_TCPSOCKET = {'url': STATS_SOCKET, 'collect_aggregates_only': False}


CHECK_CONFIG = {
    'url': STATS_URL,
    'username': USERNAME,
    'password': PASSWORD,
    'status_check': True,
    'collect_aggregates_only': 'both',
    'tag_service_check_by_host': True,
    'active_tag': True,
}

CHECK_CONFIG_OPEN = {'url': STATS_URL_OPEN, 'collect_aggregates_only': False, 'collect_status_metrics': True}

BACKEND_SERVICES = ['anotherbackend', 'datadog']

BACKEND_LIST = ['singleton:8080', 'singleton:8081', 'otherserver']

BACKEND_TO_ADDR = {
    'singleton:8080': '127.0.0.1:8080',
    'singleton:8081': '127.0.0.1:8081',
    'otherserver': '127.0.0.1:1234',
}


BACKEND_HOSTS_METRIC = 'haproxy.backend_hosts'
BACKEND_STATUS_METRIC = 'haproxy.count_per_status'

FRONTEND_CHECK = [
    # gauges
    ('haproxy.frontend.session.current', ['1', '0']),
    ('haproxy.frontend.session.limit', ['1', '0']),
    ('haproxy.frontend.session.pct', ['1', '0']),
    ('haproxy.frontend.requests.rate', ['1', '4']),
    ('haproxy.frontend.connections.rate', ['1', '7']),
    # rates
    ('haproxy.frontend.bytes.in_rate', ['1', '0']),
    ('haproxy.frontend.bytes.out_rate', ['1', '0']),
    ('haproxy.frontend.denied.req_rate', ['1', '0']),
    ('haproxy.frontend.denied.resp_rate', ['1', '0']),
    ('haproxy.frontend.errors.req_rate', ['1', '0']),
    ('haproxy.frontend.session.rate', ['1', '0']),
    ('haproxy.frontend.response.1xx', ['1', '4']),
    ('haproxy.frontend.response.2xx', ['1', '4']),
    ('haproxy.frontend.response.3xx', ['1', '4']),
    ('haproxy.frontend.response.4xx', ['1', '4']),
    ('haproxy.frontend.response.5xx', ['1', '4']),
    ('haproxy.frontend.response.other', ['1', '4']),
    ('haproxy.frontend.requests.tot_rate', ['1', '4']),
    ('haproxy.frontend.connections.tot_rate', ['1', '7']),
    ('haproxy.frontend.requests.intercepted', ['1', '7']),
]

BACKEND_CHECK = [
    # gauges
    ('haproxy.backend.queue.current', ['1', '0']),
    ('haproxy.backend.session.current', ['1', '0']),
    ('haproxy.backend.queue.time', ['1', '5']),
    ('haproxy.backend.connect.time', ['1', '5']),
    ('haproxy.backend.response.time', ['1', '5']),
    ('haproxy.backend.session.time', ['1', '5']),
    ('haproxy.backend.uptime', ['1', '7']),
    # rates
    ('haproxy.backend.bytes.in_rate', ['1', '0']),
    ('haproxy.backend.bytes.out_rate', ['1', '0']),
    ('haproxy.backend.denied.resp_rate', ['1', '0']),
    ('haproxy.backend.errors.con_rate', ['1', '0']),
    ('haproxy.backend.errors.resp_rate', ['1', '0']),
    ('haproxy.backend.session.rate', ['1', '0']),
    ('haproxy.backend.warnings.redis_rate', ['1', '0']),
    ('haproxy.backend.warnings.retr_rate', ['1', '0']),
    ('haproxy.backend.response.1xx', ['1', '4']),
    ('haproxy.backend.response.2xx', ['1', '4']),
    ('haproxy.backend.response.3xx', ['1', '4']),
    ('haproxy.backend.response.4xx', ['1', '4']),
    ('haproxy.backend.response.5xx', ['1', '4']),
    ('haproxy.backend.response.other', ['1', '4']),
]

BACKEND_AGGREGATE_ONLY_CHECK = [
    # gauges
    ('haproxy.backend.uptime', ['1', '0']),
    ('haproxy.backend.session.limit', ['1', '0']),
    ('haproxy.backend.session.pct', ['1', '5']),
    # rates
    ('haproxy.backend.denied.req_rate', ['1', '0']),
    ('haproxy.backend.requests.tot_rate', ['1', '7']),
]

SERVICE_CHECK_NAME = 'haproxy.backend_up'
