# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import BROKER_NAMESPACE, CONTROLLER_NAMESPACE, MINION_NAMESPACE, SERVER_NAMESPACE

pytestmark = pytest.mark.e2e


def test_check(dd_agent_check, e2e_instance):
    """
    Test that the Pinot check collects metrics from a real multi-container Pinot cluster.

    ZooKeeper plus four JVMs (Controller, Server, Broker, Minion) each run the JMX Prometheus
    exporter on a distinct port (host 18009–18006 → container 8009–8006). The check is
    configured with one metrics URL per component so each namespace scrapes its own process.
    A one-shot bootstrap service loads the batch baseballStats table before assertions run.
    """
    aggregator = dd_agent_check(e2e_instance, rate=True)

    for namespace in (CONTROLLER_NAMESPACE, SERVER_NAMESPACE, BROKER_NAMESPACE, MINION_NAMESPACE):
        aggregator.assert_metric(f'{namespace}.can_connect', value=1)

    metadata_metrics = get_metadata_metrics()

    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )
