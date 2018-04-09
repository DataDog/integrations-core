import os

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
HOST = os.getenv('DOCKER_HOSTNAME', 'localhost')
PORT = '3835'
PORT_OPEN = '3836'
BASE_URL = "http://{0}:{1}".format(HOST, PORT)
BASE_URL_OPEN = "http://{0}:{1}".format(HOST, PORT_OPEN)
STATUS_URL = "{0}/status".format(BASE_URL)
STATUS_URL_OPEN = "{0}/status".format(BASE_URL_OPEN)
