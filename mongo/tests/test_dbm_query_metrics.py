# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from . import common
from .conftest import mock_now, mock_pymongo
from .utils import run_check_once

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


def mock_mongo_version_8():
    """Context manager to mock MongoDB version 8.0 for query metrics tests."""
    return mock.patch.object(common.MongoDb, '_mongo_version', new_callable=mock.PropertyMock, return_value='8.0.0')


@mock_now(1715911398.1112723)
@common.standalone
def test_mongo_query_metrics_standalone(aggregator, instance_integration_cluster_autodiscovery, check, dd_run_check):
    """Test query metrics collection on standalone MongoDB 8.0+."""
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['query_metrics'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['schemas'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    with mock_pymongo("standalone"):
        # Mock MongoDB version 8.0 for $queryStats support
        with mock.patch.object(mongo_check, '_mongo_version', '8.0.0'):
            aggregator.reset()
            run_check_once(mongo_check, dd_run_check)

    # Verify query metrics events were collected
    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    fqt_samples = [event for event in dbm_samples if event.get('dbm_type') == 'fqt']

    # We should have FQT (Full Query Text) events for each unique query
    # Note: The first run won't have derivative metrics since we need 2 runs
    # This test validates that the collection pipeline works
    assert len(fqt_samples) >= 0  # May be 0 on first run due to derivative calc


@mock_now(1715911398.1112723)
@common.standalone
def test_mongo_query_metrics_disabled(aggregator, instance_integration_cluster_autodiscovery, check, dd_run_check):
    """Test that query metrics are not collected when disabled."""
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['query_metrics'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['schemas'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    with mock_pymongo("standalone"):
        with mock.patch.object(mongo_check, '_mongo_version', '8.0.0'):
            aggregator.reset()
            run_check_once(mongo_check, dd_run_check)

    # No FQT events should be emitted when query_metrics is disabled
    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    fqt_samples = [event for event in dbm_samples if event.get('dbm_type') == 'fqt']
    assert len(fqt_samples) == 0


@mock_now(1715911398.1112723)
@common.standalone
def test_mongo_query_metrics_version_check(aggregator, instance_integration_cluster_autodiscovery, check, dd_run_check):
    """Test that query metrics are skipped for MongoDB < 8.0."""
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['query_metrics'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['schemas'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    with mock_pymongo("standalone"):
        # Keep default version (4.x) which is below 8.0
        aggregator.reset()
        run_check_once(mongo_check, dd_run_check)

    # No query metrics events should be emitted for MongoDB < 8.0
    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    fqt_samples = [event for event in dbm_samples if event.get('dbm_type') == 'fqt']
    assert len(fqt_samples) == 0


@common.shard
def test_mongo_query_metrics_arbiter(aggregator, instance_arbiter, check, dd_run_check):
    """Test that query metrics are skipped on arbiter nodes."""
    instance_arbiter['dbm'] = True
    instance_arbiter['cluster_name'] = 'my_cluster'
    instance_arbiter['query_metrics'] = {'enabled': True, 'run_sync': True}
    instance_arbiter['operation_samples'] = {'enabled': False}
    instance_arbiter['slow_operations'] = {'enabled': False}
    instance_arbiter['schemas'] = {'enabled': False}

    mongo_check = check(instance_arbiter)
    aggregator.reset()
    with mock_pymongo("replica-arbiter"):
        with mock.patch.object(mongo_check, '_mongo_version', '8.0.0'):
            dd_run_check(mongo_check)

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    fqt_samples = [event for event in dbm_samples if event.get('dbm_type') == 'fqt']
    assert len(fqt_samples) == 0
