# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import psycopg2
import pytest

from .common import DB_NAME, HOST, assert_metric_at_least
from .utils import requires_over_10

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@requires_over_10
def test_physical_replication_slots(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    redo_lsn_age = 0
    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        with conn.cursor() as cur:
            cur.execute("select pg_wal_lsn_diff(pg_current_wal_lsn(), redo_lsn) from pg_control_checkpoint();")
            redo_lsn_age = int(cur.fetchall()[0][0])

            cur.execute("select * from pg_create_physical_replication_slot('phys_1');")
            cur.execute("select * from pg_create_physical_replication_slot('phys_2', true);")
            cur.execute("select * from pg_create_physical_replication_slot('phys_3', true, true);")

    time.sleep(0.2)
    check.check(pg_instance)

    #     slot_name     | slot_type | temporary | active | active_pid | xmin | restart_lsn
    # ------------------+-----------+-----------+--------+------------+------+-------------
    #  replication_slot | physical  | f         | t      |         99 |  806 | 0/30385B0
    #  phys_1           | physical  | f         | f      |            |      |
    #  phys_2           | physical  | f         | f      |            |      | 0/2000028
    #  phys_3           | physical  | t         | t      |        344 |      | 0/2000028

    # Nothing reported for phys_1
    expected_phys2_tags = pg_instance['tags'] + [
        'port:{}'.format(pg_instance['port']),
        'slot_name:phys_2',
        'slot_persistence:permanent',
        'slot_state:inactive',
        'slot_type:physical',
    ]
    expected_phys3_tags = pg_instance['tags'] + [
        'port:{}'.format(pg_instance['port']),
        'slot_name:phys_3',
        'slot_persistence:temporary',
        'slot_state:active',
        'slot_type:physical',
    ]
    expected_repslot_tags = pg_instance['tags'] + [
        'port:{}'.format(pg_instance['port']),
        'slot_name:replication_slot',
        'slot_persistence:permanent',
        'slot_state:active',
        'slot_type:physical',
    ]

    assert_metric_at_least(
        aggregator,
        'postgresql.replication_slot.restart_delay_bytes',
        lower_bound=redo_lsn_age,
        tags=expected_phys2_tags,
        count=1,
    )

    assert_metric_at_least(
        aggregator,
        'postgresql.replication_slot.restart_delay_bytes',
        lower_bound=redo_lsn_age,
        tags=expected_phys3_tags,
        count=1,
    )
    aggregator.assert_metric('postgresql.replication_slot.xmin_age', count=1, value=0, tags=expected_repslot_tags)


@requires_over_10
def test_logical_replication_slots(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) FROM pg_replication_slots;")
            restart_age = cur.fetchall()[0][0]

    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + [
        'port:{}'.format(pg_instance['port']),
        'slot_name:logical_slot',
        'slot_persistence:permanent',
        'slot_state:inactive',
        'slot_type:logical',
    ]
    # Both should be in the past
    assert_metric_at_least(
        aggregator,
        'postgresql.replication_slot.confirmed_flush_delay_bytes',
        count=1,
        lower_bound=50,
        tags=expected_tags,
    )
    assert_metric_at_least(
        aggregator,
        'postgresql.replication_slot.restart_delay_bytes',
        count=1,
        lower_bound=restart_age,
        tags=expected_tags,
    )
