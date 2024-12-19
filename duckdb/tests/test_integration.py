# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.duckdb import DuckdbCheck

from . import common


def test_check(dd_run_check, aggregator, instance):
    instance = common.DEFAULT_INSTANCE
    check = DuckdbCheck('duckdb', {}, [instance])
    dd_run_check(check)

    for metric in common.METRICS_MAP:
        aggregator.assert_metric(metric)

def test_version(dd_run_check, aggregator, instance, datadog_agent):
    instance = common.DEFAULT_INSTANCE
    check = DuckdbCheck('duckdb', {}, [instance])
    check.check_id = 'test:123'
    raw_version = '1.1.1'
    major, minor, patch = raw_version.split('.')
    version_metadata = {
            'version.scheme': 'semver',
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.raw': raw_version,
        }
    dd_run_check(check)

    datadog_agent.assert_metadata('test:123', version_metadata)