# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""How the server's timeouts treat a task statement whose rows the check reads slowly."""

from __future__ import annotations

import time
from copy import deepcopy
from unittest.mock import patch

import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.data_observability import EVENT_TRACK_TYPE
from datadog_checks.mysql.do_query import DOQuerySession

from . import common

TABLE = 'testdb.do_stream'
# 2^18 rows of 200 bytes, about 50 MB: far more than the socket buffers hold, so the server is still
# writing rows long after the query starts.
TABLE_ROWS = 2**18
QUERY = f"SELECT id, REPEAT('x', 200) AS payload FROM {TABLE}"


@pytest.fixture
def stream_table(root_conn):
    with root_conn.cursor() as cursor:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {TABLE} (id INT NOT NULL PRIMARY KEY)")
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE}")
        (count,) = cursor.fetchone()
        if count == 0:
            cursor.execute(f"INSERT INTO {TABLE} (id) VALUES (0)")
            count = 1
        while count < TABLE_ROWS:
            cursor.execute(f"INSERT INTO {TABLE} (id) SELECT id + %s FROM {TABLE}", (count,))
            count *= 2
        cursor.execute(f"GRANT SELECT ON {TABLE} TO 'dog'@'%'")
    root_conn.commit()


def _run_task(dd_run_check, instance_basic, timeout_seconds):
    instance = deepcopy(instance_basic)
    instance.update(
        {
            'run_once': True,
            'do_task': {
                'config_id': 'do-mysql-once-streaming',
                'task_id': 'streaming',
                'expires_at': int(time.time()) + 600,
                'statements': [
                    {
                        'id': 's0',
                        'dbname': 'testdb',
                        'query': QUERY,
                        'timeout_seconds': timeout_seconds,
                        'max_rows': TABLE_ROWS,
                    }
                ],
            },
        }
    )
    dd_run_check(MySql(common.CHECK_NAME, {}, [instance]))


def _slow_batches(pause):
    """Wrap DOQuerySession._batches so the check pauses `pause(batch_number)` seconds per batch."""
    batches = DOQuerySession._batches

    def slow(self, cursor, max_rows, batch_rows):
        for number, batch in enumerate(batches(self, cursor, max_rows, batch_rows)):
            time.sleep(pause(number))
            yield batch

    return slow


def _final_and_chunks(aggregator):
    events = aggregator.get_event_platform_events(EVENT_TRACK_TYPE)
    (final,) = [event for event in events if event.get('kind') == 'final']
    return final, [event for event in events if event.get('kind') == 'chunk']


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment', 'stream_table')
def test_streaming_timeout_covers_the_transfer(aggregator, dd_run_check, instance_basic):
    # The query itself is fast, but reading 262 batches 50 ms apart takes about 13 seconds. If the
    # statement timeout (max_execution_time on MySQL, max_statement_time on MariaDB) counts the
    # transfer, the read fails after some chunks. If this fails with a successful final event, the
    # timeout covers only execution, and the design's note on timeout_seconds must change.
    with patch.object(DOQuerySession, '_batches', _slow_batches(lambda number: 0.05)):
        _run_task(dd_run_check, instance_basic, timeout_seconds=2)

    final, chunks = _final_and_chunks(aggregator)
    assert (final['status'], final['error_kind']) == ('error', 'statement_timeout'), final
    assert final['chunk_count'] == len(chunks) > 0
    assert final['row_count'] < TABLE_ROWS


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment', 'stream_table')
def test_streaming_timeout_net_write_drops_a_stalled_reader(aggregator, dd_run_check, instance_basic):
    # A pause longer than net_write_timeout while the server still has rows to send drops the
    # connection, which shows the session setting takes effect.
    with (
        patch('datadog_checks.mysql.do_task.NET_WRITE_TIMEOUT_SECONDS', 1),
        patch.object(DOQuerySession, '_batches', _slow_batches(lambda number: 5 if number == 0 else 0)),
    ):
        _run_task(dd_run_check, instance_basic, timeout_seconds=600)

    final, _ = _final_and_chunks(aggregator)
    assert (final['status'], final['error_kind']) == ('error', 'connection_error'), final
