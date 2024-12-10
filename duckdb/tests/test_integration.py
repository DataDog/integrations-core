# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import common
import pytest
import duckdb
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.duckdb import DuckdbCheck



@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check(instance, aggregator, datadog_agent, dd_run_check):
    connection = duckdb.connect(
        port=common.PORT,
        database=common.DB,
    )
    cur = connection.cursor()
    cur.execute('SELECT * FROM persons;')

    check = DuckdbCheck('duckdb', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    datadog_agent.assert_metadata('test:123')
