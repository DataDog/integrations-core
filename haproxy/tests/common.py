import os

from datadog_checks.utils.common import get_docker_hostname

AGG_STATUSES_BY_SERVICE = (
    (['status:available', 'service:a'], 1),
    (['status:available', 'service:b'], 4),
    (['status:unavailable', 'service:b'], 2),
    (['status:available', 'service:be_edge_http_sre-production_elk-kibana'], 1),
    (['status:unavailable', 'service:be_edge_http_sre-production_elk-kibana'], 2)
)

AGG_STATUSES = (
    (['status:available'], 6),
    (['status:unavailable'], 4)
)

CHECK_NAME = 'haproxy'

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
HOST = get_docker_hostname()
PORT = '13835'
PORT_OPEN = '13836'
BASE_URL = "http://{0}:{1}".format(HOST, PORT)
BASE_URL_OPEN = "http://{0}:{1}".format(HOST, PORT_OPEN)
STATS_URL = "{0}/stats".format(BASE_URL)
STATS_URL_OPEN = "{0}/stats".format(BASE_URL_OPEN)
USERNAME = 'datadog'
PASSWORD = 'isdevops'

CONFIG_UNIXSOCKET = {
    'collect_aggregates_only': False,
}


CHECK_CONFIG = {
    'url': STATS_URL,
    'username': USERNAME,
    'password': PASSWORD,
    'status_check': True,
    'collect_aggregates_only': False,
    'tag_service_check_by_host': True,
    'active_tag': True,
}

CHECK_CONFIG_OPEN = {
    'url': STATS_URL_OPEN,
    'collect_aggregates_only': False,
}

BACKEND_SERVICES = ['anotherbackend', 'datadog']

BACKEND_LIST = ['singleton:8080', 'singleton:8081', 'otherserver']

FRONTEND_CHECK_GAUGES = [
    'haproxy.frontend.session.current',
    'haproxy.frontend.session.limit',
    'haproxy.frontend.session.pct',
]

FRONTEND_CHECK_GAUGES_POST_1_4 = [
    'haproxy.frontend.requests.rate',
]

BACKEND_CHECK_GAUGES = [
    'haproxy.backend.queue.current',
    'haproxy.backend.session.current',
]

BACKEND_CHECK_GAUGES_POST_1_5 = [
    'haproxy.backend.queue.time',
    'haproxy.backend.connect.time',
    'haproxy.backend.response.time',
    'haproxy.backend.session.time',
]

FRONTEND_CHECK_RATES = [
    'haproxy.frontend.bytes.in_rate',
    'haproxy.frontend.bytes.out_rate',
    'haproxy.frontend.denied.req_rate',
    'haproxy.frontend.denied.resp_rate',
    'haproxy.frontend.errors.req_rate',
    'haproxy.frontend.session.rate',
]

FRONTEND_CHECK_RATES_POST_1_4 = [
    'haproxy.frontend.response.1xx',
    'haproxy.frontend.response.2xx',
    'haproxy.frontend.response.3xx',
    'haproxy.frontend.response.4xx',
    'haproxy.frontend.response.5xx',
    'haproxy.frontend.response.other',
]

BACKEND_CHECK_RATES = [
    'haproxy.backend.bytes.in_rate',
    'haproxy.backend.bytes.out_rate',
    'haproxy.backend.denied.resp_rate',
    'haproxy.backend.errors.con_rate',
    'haproxy.backend.errors.resp_rate',
    'haproxy.backend.session.rate',
    'haproxy.backend.warnings.redis_rate',
    'haproxy.backend.warnings.retr_rate',
]

BACKEND_CHECK_RATES_POST_1_4 = [
    'haproxy.backend.response.1xx',
    'haproxy.backend.response.2xx',
    'haproxy.backend.response.3xx',
    'haproxy.backend.response.4xx',
    'haproxy.backend.response.5xx',
    'haproxy.backend.response.other',
]

BACKEND_CHECK_GAUGES_POST_1_7 = [
    'haproxy.backend.uptime'
]

SERVICE_CHECK_NAME = 'haproxy.backend_up'
