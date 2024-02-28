# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from .common import _get_expected_tags, check_bgw_metrics, check_common_metrics
from .utils import _get_conn


@pytest.mark.e2e
def test_e2e(check, dd_agent_check, pg_instance):
    aggregator = dd_agent_check(pg_instance, rate=True)

    conn = _get_conn(pg_instance)
    with conn.cursor() as cur:
        cur.execute("SHOW server_version;")
        check.raw_version = cur.fetchone()[0]

        cur.execute("SELECT system_identifier FROM pg_control_system();")
        check.system_identifier = cur.fetchone()[0]

    expected_tags = _get_expected_tags(check, pg_instance, with_host=False)
    check_bgw_metrics(aggregator, expected_tags)
    check_common_metrics(aggregator, expected_tags=expected_tags, count=None)
