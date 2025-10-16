# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Utility module for loading JSON fixture files in tests.

This module provides helper functions to load API response fixtures
that were generated using the fetch_api_fixtures.py script.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict


FIXTURES_DIR = Path(__file__).parent


def load_fixture(filename: str) -> Dict[str, Any]:
    """
    Load a JSON fixture file.

    Args:
        filename: Name of the fixture file (e.g., 'clusters.json')

    Returns:
        Dictionary containing the parsed JSON data

    Raises:
        FileNotFoundError: If the fixture file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    fixture_path = FIXTURES_DIR / filename
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {fixture_path}")

    with open(fixture_path, 'r') as f:
        return json.load(f)


def load_clusters() -> Dict[str, Any]:
    """Load the clusters.json fixture."""
    return load_fixture('clusters.json')


def load_cluster_stats() -> Dict[str, Any]:
    """Load the cluster_stats.json fixture."""
    return load_fixture('cluster_stats.json')


def load_storage_containers() -> Dict[str, Any]:
    """Load the storage_containers.json fixture."""
    return load_fixture('storage_containers.json')


def load_hosts() -> Dict[str, Any]:
    """Load the hosts.json fixture."""
    return load_fixture('hosts.json')


def load_host_stats() -> Dict[str, Any]:
    """Load the host_stats.json fixture."""
    return load_fixture('host_stats.json')


def load_vms() -> Dict[str, Any]:
    """Load the vms.json fixture."""
    return load_fixture('vms.json')


def load_vm_stats() -> Dict[str, Any]:
    """Load the vm_stats.json fixture."""
    return load_fixture('vm_stats.json')


def load_events() -> Dict[str, Any]:
    """Load the events.json fixture."""
    return load_fixture('events.json')


def load_alerts() -> Dict[str, Any]:
    """Load the alerts.json fixture."""
    return load_fixture('alerts.json')


# Convenience function to get all fixtures as a dictionary
def load_all_fixtures() -> Dict[str, Dict[str, Any]]:
    """
    Load all available fixtures.

    Returns:
        Dictionary mapping fixture names to their data
    """
    fixture_loaders = {
        'clusters': load_clusters,
        'cluster_stats': load_cluster_stats,
        'storage_containers': load_storage_containers,
        'hosts': load_hosts,
        'host_stats': load_host_stats,
        'vms': load_vms,
        'vm_stats': load_vm_stats,
        'events': load_events,
        'alerts': load_alerts,
    }

    fixtures = {}
    for name, loader in fixture_loaders.items():
        try:
            fixtures[name] = loader()
        except FileNotFoundError:
            # Skip fixtures that don't exist yet
            pass

    return fixtures
