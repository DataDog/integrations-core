# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from .common import DB_NAME, HOST, PORT
from .test_common import check_bgw_metrics, check_common_metrics


@pytest.mark.e2e
def test_e2e(dd_agent_check, pg_instance):
    aggregator = dd_agent_check(pg_instance, rate=True)

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT)]
    check_bgw_metrics(aggregator, expected_tags)

    expected_tags += ['db:{}'.format(DB_NAME)]
    check_common_metrics(aggregator, expected_tags=expected_tags, count=None)
