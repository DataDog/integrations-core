# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import datetime
import re
import select
import time
from collections import Counter
from concurrent.futures.thread import ThreadPoolExecutor

import mock
import psycopg2
import pytest
from dateutil import parser
from semver import VersionInfo
from six import string_types

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.time import UTC
from datadog_checks.postgres.statement_samples import DBExplainError, StatementTruncationState
from datadog_checks.postgres.statements import PG_STAT_STATEMENTS_METRICS_COLUMNS, PG_STAT_STATEMENTS_TIMING_COLUMNS

from .common import DB_NAME, HOST, PORT, PORT_REPLICA2, POSTGRES_VERSION
from .utils import _get_conn, _get_superconn, requires_over_10

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.1
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}
    pg_instance['query_metadata'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    return pg_instance


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.mark.parametrize("metadata_enabled", [True, False])
def test_metadata_enabled_config(
        integration_check, dbm_instance, metadata_enabled
):
    dbm_instance["query_metadata"] = {'enabled': metadata_enabled}
    check = integration_check(dbm_instance)
    assert check.metadata_samples._enabled == metadata_enabled


def test_collect_metadata(
        integration_check, dbm_instance, aggregator
):
    check = integration_check(dbm_instance)
    check.check(dbm_instance)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = dbm_metadata[0]
    assert event['host'] == "stubbed.hostname"
    assert event['dbms'] == "postgres"
    assert event['kind'] == "metadata"
    assert len(event["metadata"]) > 0

