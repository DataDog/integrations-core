# ABOUTME: Integration tests for the NiFi integration against a real Docker NiFi instance.
# ABOUTME: Validates metric emission, auth, and metadata consistency with a running NiFi server.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.nifi import NifiCheck

from . import common


@pytest.fixture
def check(instance):
    return NifiCheck('nifi', {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
class TestIntegration:
    def test_check(self, dd_run_check, aggregator, check):
        """Full check run against real NiFi emits expected metrics."""
        dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=1)

        # System diagnostics
        aggregator.assert_metric('nifi.system.jvm.heap_used')
        aggregator.assert_metric('nifi.system.jvm.heap_max')
        aggregator.assert_metric('nifi.system.jvm.total_threads')
        aggregator.assert_metric('nifi.system.gc.collection_count')

        # Flow status
        aggregator.assert_metric('nifi.flow.running_count')
        aggregator.assert_metric('nifi.flow.stopped_count')

        # Root process group
        aggregator.assert_metric('nifi.process_group.flowfiles_queued')

    def test_check_with_connection_metrics(self, dd_run_check, aggregator, instance):
        """Connection metrics appear when opt-in is enabled."""
        instance['collect_connection_metrics'] = True
        check = NifiCheck('nifi', {}, [instance])
        dd_run_check(check)

        aggregator.assert_metric('nifi.connection.queued_count')

    def test_check_with_processor_metrics(self, dd_run_check, aggregator, instance):
        """Processor metrics appear when opt-in is enabled."""
        instance['collect_processor_metrics'] = True
        check = NifiCheck('nifi', {}, [instance])
        dd_run_check(check)

        aggregator.assert_metric('nifi.processor.flowfiles_in')
        aggregator.assert_metric('nifi.processor.run_status')

    def test_auth_failure(self, dd_run_check, aggregator, instance):
        """Wrong credentials emit can_connect=0."""
        instance['password'] = 'wrong-password'
        check = NifiCheck('nifi', {}, [instance])

        with pytest.raises(Exception):
            dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=0)

    def test_metadata_metrics(self, dd_run_check, aggregator, instance):
        """All emitted metrics are declared in metadata.csv."""
        instance['collect_connection_metrics'] = True
        instance['collect_processor_metrics'] = True
        check = NifiCheck('nifi', {}, [instance])
        dd_run_check(check)

        aggregator.assert_metrics_using_metadata(get_metadata_metrics())
