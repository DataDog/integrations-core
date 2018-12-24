# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import logging
import requests

from . import common
from datadog_checks.twemproxy import Twemproxy


log = logging.getLogger('test_twemproxy')


GLOBAL_STATS = set([
    'curr_connections',
    'total_connections'
])

POOL_STATS = set([
    'client_eof',
    'client_err',
    'client_connections',
    'server_ejects',
    'forward_error',
    'fragments'
])

SERVER_STATS = set([
    'in_queue',
    'out_queue',
    'in_queue_bytes',
    'out_queue_bytes',
    'server_connections',
    'server_timedout',
    'server_err',
    'server_eof',
    'requests',
    'request_bytes',
    'responses',
    'response_bytes',
])

SC_TAGS = ['host:{}'.format(common.HOST), 'port:{}'.format(common.PORT), 'optional:tag1']


@pytest.fixture
def check():
    check = Twemproxy('twemproxy', {}, {})
    return check


@pytest.fixture
def setup_request():
    """
    A request needs to be made in order for some of the data to be seeded
    """
    url = "http://{}:{}".format(common.HOST, common.PORT)
    try:
        requests.get(url)
    except Exception:
        pass


def test_check(check, dd_environment, setup_request, aggregator):
    check.check(common.INSTANCE)

    for stat in GLOBAL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), at_least=0)
    for stat in POOL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=1)
    for stat in SERVER_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=2)

    # Test service check
    aggregator.assert_service_check('twemproxy.can_connect', status=Twemproxy.OK,
                                    tags=SC_TAGS, count=1)

    # Raises when COVERAGE=true and coverage < 100%
    aggregator.assert_all_metrics_covered()
