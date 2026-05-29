# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Script to record fixtures from a live Nutanix Prism Central instance.

This script connects to the AWS_INSTANCE defined in conftest.py and records
all API responses as JSON fixtures for testing.

Usage:
    python record_fixtures.py                          # record all resources
    python record_fixtures.py -r disks,hosts           # record only disks and hosts
    python record_fixtures.py --resources host_stats   # record host_stats (auto-fetches deps in memory)
    python record_fixtures.py --list                   # list available resources

Dependency resolution:
    Resources like ``hosts``, ``cluster_stats``, ``host_stats`` depend on the
    cluster list. When you request only a dependent resource, its dependencies
    are fetched in memory so the request can be fulfilled, but their fixtures
    are not overwritten unless they are also requested.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import AWS_INSTANCE  # noqa: E402
from requests.auth import HTTPBasicAuth  # noqa: E402

RESOURCES = (
    "clusters",
    "categories",
    "hosts",
    "cluster_stats",
    "host_stats",
    "vms",
    "vm_stats",
    "disks",
    "events",
    "audits",
    "alerts",
    "tasks",
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
FIXTURES_DIR.mkdir(exist_ok=True)

# Extract config
PC_IP = AWS_INSTANCE["pc_ip"]
PC_PORT = AWS_INSTANCE["pc_port"]
PC_USERNAME = AWS_INSTANCE["pc_username"]
PC_PASSWORD = AWS_INSTANCE["pc_password"]
TLS_VERIFY = AWS_INSTANCE["tls_verify"]
PAGE_LIMIT = AWS_INSTANCE["page_limit"]

# Build base URL
BASE_URL = PC_IP
if not BASE_URL.startswith("http"):
    BASE_URL = f"https://{BASE_URL}"
BASE_URL = f"{BASE_URL}:{PC_PORT}"

# Create session with auth
session = requests.Session()
session.auth = HTTPBasicAuth(PC_USERNAME, PC_PASSWORD)
session.verify = TLS_VERIFY


def make_request(endpoint: str, params: dict | None = None) -> requests.Response:
    """Make a request to the Nutanix API.

    Args:
        endpoint: API endpoint path (e.g., "api/clustermgmt/v4.0/config/clusters")
        params: Query parameters

    Returns:
        Response object
    """
    url = f"{BASE_URL}/{endpoint}"
    print(f"  GET {endpoint}")
    if params:
        print(f"    params: {params}")
    response = session.get(url, params=params)
    response.raise_for_status()
    return response


def fetch_paginated_endpoint(endpoint: str, params: dict | None = None) -> list[dict]:
    """Fetch all pages from a paginated endpoint.

    Args:
        endpoint: API endpoint path
        params: Base query parameters

    Returns:
        List of page responses (each page is a full API response dict)
    """
    print(f"Fetching paginated endpoint: {endpoint}")
    pages = []
    page = 0

    # Copy params
    req_params = {} if params is None else params.copy()
    req_params["$page"] = page
    req_params["$limit"] = PAGE_LIMIT

    while True:
        response = make_request(endpoint, params=req_params)
        payload = response.json()
        pages.append(payload)

        # Check if there's more data
        data = payload.get("data", [])
        if not data:
            break

        # Check for next link
        links = payload.get("metadata", {}).get("links", [])
        next_link = next((link.get("href") for link in links if link.get("rel") == "next"), None)

        if not next_link:
            break

        page += 1
        req_params["$page"] = page
        print(f"  Fetched page {page}")

    print(f"  Total pages: {len(pages)}")
    return pages


def fetch_non_paginated_endpoint(endpoint: str, params: dict | None = None) -> dict:
    """Fetch a non-paginated endpoint.

    Args:
        endpoint: API endpoint path
        params: Query parameters

    Returns:
        API response dict
    """
    print(f"Fetching non-paginated endpoint: {endpoint}")
    response = make_request(endpoint, params=params)
    return response.json()


def save_fixture(filename: str, data: list | dict) -> None:
    """Save data as a JSON fixture file.

    Args:
        filename: Fixture filename (e.g., "clusters.json")
        data: Data to save
    """
    filepath = FIXTURES_DIR / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✓ Saved {filepath}")


def record_clusters(save: bool = True) -> list[dict]:
    """Record clusters fixture.

    Returns:
        List of cluster objects (for further processing)
    """
    pages = fetch_paginated_endpoint("api/clustermgmt/v4.0/config/clusters")
    if save:
        save_fixture("clusters.json", pages)

    # Extract cluster data for return
    clusters = []
    for page in pages:
        clusters.extend(page.get("data", []))
    return clusters


def record_categories() -> None:
    """Record categories fixture."""
    pages = fetch_paginated_endpoint("api/prism/v4.0/config/categories")
    save_fixture("categories.json", pages)


def record_hosts(clusters: list[dict], save: bool = True) -> list[tuple[str, str]]:
    """Record hosts fixtures for each cluster.

    Args:
        clusters: List of cluster objects
        save: Persist the fixtures to disk. When False, hosts are still fetched
            (for the returned cluster/host id pairs) but no fixture is written.

    Returns:
        List of (cluster_id, host_id) tuples for further processing
    """
    cluster_host_pairs = []

    for cluster in clusters:
        cluster_id = cluster.get("extId")
        cluster_name = cluster.get("name", "unknown")

        if not cluster_id:
            continue

        print(f"\nRecording hosts for cluster: {cluster_name} ({cluster_id})")

        try:
            # Fetch hosts for this cluster
            pages = fetch_paginated_endpoint(f"api/clustermgmt/v4.0/config/clusters/{cluster_id}/hosts")

            if save:
                # Use shortened cluster ID (first 8 chars) for filename
                short_cluster_id = cluster_id.split("-")[0]
                save_fixture(f"hosts_{short_cluster_id}.json", pages)

            # Collect host IDs
            for page in pages:
                for host in page.get("data", []):
                    host_id = host.get("extId")
                    if host_id:
                        cluster_host_pairs.append((cluster_id, host_id))
        except requests.exceptions.HTTPError as e:
            print(f"  ⚠ Failed to fetch hosts for this cluster: {e}")
            print("  (This is expected for Prism Central deployment clusters)")

    return cluster_host_pairs


def record_cluster_stats(clusters: list[dict]) -> None:
    """Record cluster stats fixtures.

    Args:
        clusters: List of cluster objects
    """
    # Calculate time window (similar to InfrastructureMonitor)
    now = datetime.now(timezone.utc)
    sampling_interval = 120  # Default from check
    end_time = now - timedelta(seconds=sampling_interval)
    start_time = end_time - timedelta(seconds=sampling_interval)

    start_time_str = start_time.isoformat()
    end_time_str = end_time.isoformat()

    for cluster in clusters:
        cluster_id = cluster.get("extId")
        cluster_name = cluster.get("name", "unknown")

        if not cluster_id:
            continue

        print(f"\nRecording cluster stats for: {cluster_name} ({cluster_id})")

        params = {
            "$startTime": start_time_str,
            "$endTime": end_time_str,
            "$statType": "AVG",
            "$samplingInterval": sampling_interval,
        }

        try:
            data = fetch_non_paginated_endpoint(f"api/clustermgmt/v4.0/stats/clusters/{cluster_id}", params=params)

            # Use shortened cluster ID for filename
            short_cluster_id = cluster_id.split("-")[0]
            save_fixture(f"cluster_stats_{short_cluster_id}.json", data)
        except requests.exceptions.HTTPError as e:
            print(f"  ⚠ Failed to fetch cluster stats: {e}")


def record_host_stats(cluster_host_pairs: list[tuple[str, str]]) -> None:
    """Record host stats fixtures.

    Args:
        cluster_host_pairs: List of (cluster_id, host_id) tuples
    """
    # Calculate time window
    now = datetime.now(timezone.utc)
    sampling_interval = 120
    end_time = now - timedelta(seconds=sampling_interval)
    start_time = end_time - timedelta(seconds=sampling_interval)

    start_time_str = start_time.isoformat()
    end_time_str = end_time.isoformat()

    for cluster_id, host_id in cluster_host_pairs:
        print(f"\nRecording host stats for cluster={cluster_id[:8]}..., host={host_id[:8]}...")

        params = {
            "$startTime": start_time_str,
            "$endTime": end_time_str,
            "$statType": "AVG",
            "$samplingInterval": sampling_interval,
        }

        try:
            data = fetch_non_paginated_endpoint(
                f"api/clustermgmt/v4.0/stats/clusters/{cluster_id}/hosts/{host_id}", params=params
            )

            # Use shortened IDs for filename
            short_cluster_id = cluster_id.split("-")[0]
            short_host_id = host_id.split("-")[0]
            save_fixture(f"host_stats_{short_cluster_id}_{short_host_id}.json", data)
        except requests.exceptions.HTTPError as e:
            print(f"  ⚠ Failed to fetch host stats: {e}")


def record_vms() -> None:
    """Record VMs fixture."""
    print("\nRecording VMs (all clusters)")
    pages = fetch_paginated_endpoint("api/vmm/v4.0/ahv/config/vms")
    save_fixture("vms.json", pages)


def record_vm_stats() -> None:
    """Record VM stats fixtures."""
    # Calculate time window
    now = datetime.now(timezone.utc)
    sampling_interval = 120
    end_time = now - timedelta(seconds=sampling_interval)
    start_time = end_time - timedelta(seconds=sampling_interval)

    start_time_str = start_time.isoformat()
    end_time_str = end_time.isoformat()

    print("\nRecording VM stats (all clusters)")

    params = {
        "$startTime": start_time_str,
        "$endTime": end_time_str,
        "$statType": "AVG",
        "$samplingInterval": sampling_interval,
        "$select": "*",
    }

    try:
        pages = fetch_paginated_endpoint("api/vmm/v4.0/ahv/stats/vms", params=params)
        save_fixture("vms_stats.json", pages)
    except requests.exceptions.HTTPError as e:
        print(f"  ⚠ Failed to fetch VM stats: {e}")


def record_disks() -> None:
    """Record disks fixture from the cluster-wide /config/disks endpoint."""
    print("\nRecording disks (all clusters)")
    try:
        pages = fetch_paginated_endpoint("api/clustermgmt/v4.0/config/disks")
        save_fixture("disks.json", pages)
    except requests.exceptions.HTTPError as e:
        print(f"  ⚠ Failed to fetch disks: {e}")


def record_events() -> None:
    """Record events fixture."""
    # Get events from last 24 hours
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)
    start_time_str = start_time.isoformat().replace("+00:00", "Z")

    print(f"\nRecording events (from {start_time_str})")

    params = {
        "$filter": f"creationTime gt {start_time_str}",
        "$orderBy": "creationTime asc",
    }

    try:
        pages = fetch_paginated_endpoint("api/monitoring/v4.0/serviceability/events", params=params)
        save_fixture("events.json", pages)
    except requests.exceptions.HTTPError as e:
        print(f"  ⚠ Failed to fetch events: {e}")


def record_audits() -> None:
    """Record audits fixture."""
    # Get audits from last 24 hours
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)
    start_time_str = start_time.isoformat().replace("+00:00", "Z")

    print(f"\nRecording audits (from {start_time_str})")

    params = {
        "$filter": f"creationTime gt {start_time_str}",
        "$orderBy": "creationTime asc",
    }

    try:
        pages = fetch_paginated_endpoint("api/monitoring/v4.0/serviceability/audits", params=params)
        save_fixture("audits.json", pages)
    except requests.exceptions.HTTPError as e:
        print(f"  ⚠ Failed to fetch audits: {e}")


def record_alerts() -> None:
    """Record alerts fixture."""
    # Get alerts from last 24 hours
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)
    start_time_str = start_time.isoformat().replace("+00:00", "Z")

    print(f"\nRecording alerts (from {start_time_str})")

    params = {
        "$filter": f"creationTime gt {start_time_str}",
        "$orderBy": "creationTime asc",
    }

    # Try v4.2 first, fallback to v4.0
    try:
        print("  Trying alerts API v4.2...")
        pages = fetch_paginated_endpoint("api/monitoring/v4.2/serviceability/alerts", params=params)
        save_fixture("alerts.json", pages)
    except requests.exceptions.HTTPError as e:
        print(f"  ⚠ v4.2 failed: {e}")
        try:
            print("  Falling back to alerts API v4.0...")
            # v4.0 doesn't support filters
            params_v40 = {}
            pages = fetch_paginated_endpoint("api/monitoring/v4.0/serviceability/alerts", params=params_v40)
            save_fixture("alerts.json", pages)
        except requests.exceptions.HTTPError as e2:
            print(f"  ⚠ v4.0 also failed: {e2}")


def record_tasks() -> None:
    """Record tasks fixture."""
    # Get tasks from last 24 hours
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)
    start_time_str = start_time.isoformat().replace("+00:00", "Z")

    print(f"\nRecording tasks (from {start_time_str})")

    params = {
        "$filter": f"createdTime gt {start_time_str}",
        "$orderBy": "createdTime asc",
    }

    try:
        pages = fetch_paginated_endpoint("api/prism/v4.0/config/tasks", params=params)
        save_fixture("tasks.json", pages)
    except requests.exceptions.HTTPError as e:
        print(f"  ⚠ Failed to fetch tasks: {e}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    ``--resources`` accepts a comma-separated list or repeated flags. The default
    is every known resource. ``--list`` prints the available names and exits.
    """
    parser = argparse.ArgumentParser(
        description="Record Nutanix fixtures for testing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available resources: {', '.join(RESOURCES)}",
    )
    parser.add_argument(
        "-r",
        "--resources",
        action="append",
        help="Resources to refresh (comma-separated or repeated). Default: all.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available resources and exit.",
    )
    return parser.parse_args(argv)


def resolve_requested_resources(args: argparse.Namespace) -> set[str]:
    """Flatten ``--resources`` values, validate against ``RESOURCES``."""
    if not args.resources:
        return set(RESOURCES)

    requested: set[str] = set()
    for entry in args.resources:
        for name in entry.split(","):
            name = name.strip()
            if name:
                requested.add(name)

    invalid = requested - set(RESOURCES)
    if invalid:
        raise SystemExit(f"Unknown resource(s): {', '.join(sorted(invalid))}. Available: {', '.join(RESOURCES)}")
    return requested


def record_selected(requested: set[str]) -> None:
    """Run the recorders for ``requested``, fetching dependencies in memory as needed."""
    needs_clusters = requested & {"clusters", "hosts", "cluster_stats", "host_stats"}
    needs_hosts = requested & {"hosts", "host_stats"}

    clusters: list[dict] = []
    cluster_host_pairs: list[tuple[str, str]] = []

    if needs_clusters:
        print("\n" + "=" * 80)
        print("INFRASTRUCTURE CONFIG")
        print("=" * 80)
        clusters = record_clusters(save="clusters" in requested)

    if "categories" in requested:
        record_categories()

    if needs_hosts:
        cluster_host_pairs = record_hosts(clusters, save="hosts" in requested)

    if requested & {"cluster_stats", "host_stats"}:
        print("\n" + "=" * 80)
        print("INFRASTRUCTURE STATS")
        print("=" * 80)
        if "cluster_stats" in requested:
            record_cluster_stats(clusters)
        if "host_stats" in requested:
            record_host_stats(cluster_host_pairs)

    if requested & {"vms", "vm_stats", "disks"}:
        print("\n" + "=" * 80)
        print("VIRTUAL MACHINES & DISKS")
        print("=" * 80)
        if "vms" in requested:
            record_vms()
        if "vm_stats" in requested:
            record_vm_stats()
        if "disks" in requested:
            record_disks()

    if requested & {"events", "audits", "alerts", "tasks"}:
        print("\n" + "=" * 80)
        print("ACTIVITY & EVENTS")
        print("=" * 80)
        if "events" in requested:
            record_events()
        if "audits" in requested:
            record_audits()
        if "alerts" in requested:
            record_alerts()
        if "tasks" in requested:
            record_tasks()


def main(argv: list[str] | None = None) -> None:
    """Main entry point for fixture recording."""
    args = parse_args(argv)

    if args.list:
        print("Available resources:")
        for name in RESOURCES:
            print(f"  - {name}")
        return

    requested = resolve_requested_resources(args)

    print("=" * 80)
    print("Nutanix Fixture Recording Script")
    print("=" * 80)
    print(f"\nConnecting to: {BASE_URL}")
    print(f"Username: {PC_USERNAME}")
    print(f"TLS Verify: {TLS_VERIFY}")
    print(f"Page Limit: {PAGE_LIMIT}")
    print(f"\nFixtures directory: {FIXTURES_DIR}")
    print(f"Resources to record: {', '.join(sorted(requested))}")
    print("=" * 80)

    # Test connectivity
    try:
        print("\nTesting connectivity...")
        response = session.get(f"{BASE_URL}/console")
        response.raise_for_status()
        print("✓ Connection successful")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return

    try:
        record_selected(requested)
        print("\n" + "=" * 80)
        print("✓ Fixtures recorded successfully!")
        print("=" * 80)
    except Exception as e:
        print(f"\n✗ Error during fixture recording: {e}")
        raise


if __name__ == "__main__":
    main()
