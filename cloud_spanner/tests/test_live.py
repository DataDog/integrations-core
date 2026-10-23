# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
#
# Live connectivity test against a real Cloud Spanner instance.
# Stubs out metric submission — prints the payload that would be sent instead.
#
# Usage:
#   SPANNER_PROJECT=dd-sbx-dbmdev1 \
#   SPANNER_INSTANCE=<instance_id> \
#   SPANNER_DATABASE=<database> \
#   SPANNER_CREDENTIALS=/home/bits/dd/integrations-core/dbm-agent-key.json \
#   hatch run test -- tests/test_live.py -v -s

import json
import os
from unittest.mock import patch

import pytest

from datadog_checks.cloud_spanner import SpannerCheck

pytestmark = pytest.mark.live

PROJECT = os.environ.get('SPANNER_PROJECT', 'dd-sbx-dbmdev1')
INSTANCE = os.environ.get('SPANNER_INSTANCE', '')
DATABASE = os.environ.get('SPANNER_DATABASE', '')
CREDENTIALS = os.environ.get('SPANNER_CREDENTIALS', '/home/bits/dd/integrations-core/dbm-agent-key.json')


@pytest.fixture
def live_instance_config():
    missing = [v for name, v in [('SPANNER_INSTANCE', INSTANCE), ('SPANNER_DATABASE', DATABASE)] if not v]
    if missing:
        pytest.skip("Set SPANNER_INSTANCE and SPANNER_DATABASE env vars to run live tests")
    return {
        'project_id': PROJECT,
        'instance_id': INSTANCE,
        'database': DATABASE,
        'dbm': True,
        'credentials_path': CREDENTIALS,
        'query_metrics': {
            'enabled': True,
            'collection_interval': 10,
        },
        'tags': ['env:staging', 'team:dbm'],
    }


def test_live_connectivity_and_payload(live_instance_config):
    check = SpannerCheck('cloud_spanner', {}, [live_instance_config])

    captured = []

    def capture_payload(payload_json):
        captured.append(json.loads(payload_json))

    with patch.object(check, 'database_monitoring_query_metrics', side_effect=capture_payload):
        error = check.run()

    assert not error, f"Check run failed: {error}"
    assert captured, (
        "No payload was emitted — QUERY_STATS_TOP_MINUTE may be empty. "
        "Run some queries against the database and wait ~1 minute for the stats table to populate."
    )

    payload = captured[0]

    print("\n" + json.dumps(payload, indent=2))

    assert payload['spanner_version'] == 'spanner'
    assert payload['host'] == f"{PROJECT}:{INSTANCE}"
    assert 'spanner_rows' in payload
    for row in payload['spanner_rows']:
        assert row['database'] == DATABASE
        assert 'query_signature' in row
        assert 'text' in row
