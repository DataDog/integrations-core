#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Mock Nutanix Prism Central API server for integration tests.
Serves fixtures from tests/fixtures/ directory with pagination support.
"""

import json
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

FIXTURES_DIR = Path('/fixtures') if Path('/fixtures').exists() else Path(__file__).parent.parent / 'fixtures'

_fixture_cache = {}


def load_fixture(filename):
    """Load a JSON fixture file and return its content."""
    if filename in _fixture_cache:
        return _fixture_cache[filename]

    fixture_path = FIXTURES_DIR / filename
    if not fixture_path.exists():
        return None

    with open(fixture_path) as f:
        data = json.load(f)
        _fixture_cache[filename] = data
        return data


def load_fixture_page(filename, page):
    """Load a specific page from a consolidated fixture file."""
    pages = load_fixture(filename)
    if not pages:
        return None
    if page < len(pages):
        return pages[page]
    # Return empty response for pages beyond available data
    return {"data": [], "metadata": {"totalAvailableResults": 0}}


def apply_time_filter(data, filter_param, time_field):
    """Apply time-based filtering to data."""
    if not filter_param or f'{time_field} gt' not in filter_param:
        return data

    filter_time_str = filter_param.split(f'{time_field} gt ')[-1].strip()
    filter_time = datetime.fromisoformat(filter_time_str.replace('Z', '+00:00'))

    filtered_items = []
    for item in data.get('data', []):
        item_time_str = item.get(time_field, '')
        if item_time_str:
            item_time = datetime.fromisoformat(item_time_str.replace('Z', '+00:00'))
            if item_time > filter_time:
                filtered_items.append(item)

    filtered_items.sort(key=lambda t: datetime.fromisoformat(t.get(time_field, '').replace('Z', '+00:00')))

    result = dict(data)
    result['data'] = filtered_items
    return result


@app.route('/console')
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route('/api/clustermgmt/v4.0/stats/clusters/<cluster_id>')
def cluster_stats(cluster_id):
    """Cluster stats endpoint (non-paginated)."""
    short_id = cluster_id.split('-')[0]
    filename = f'cluster_stats_{short_id}.json'
    data = load_fixture(filename)
    if data is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(data)


@app.route('/api/clustermgmt/v4.0/stats/clusters/<cluster_id>/hosts/<host_id>')
def host_stats(cluster_id, host_id):
    """Host stats endpoint (non-paginated)."""
    short_cluster_id = cluster_id.split('-')[0]
    short_host_id = host_id.split('-')[0]
    filename = f'host_stats_{short_cluster_id}_{short_host_id}.json'
    data = load_fixture(filename)
    if data is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(data)


@app.route('/api/clustermgmt/v4.0/config/clusters/<cluster_id>/hosts')
def cluster_hosts(cluster_id):
    """Hosts for specific cluster (paginated)."""
    page = int(request.args.get('$page', 0))

    if cluster_id == 'd07db284-6df6-4ca2-88cd-9dd5ed71ac08':
        return jsonify({"error": "Bad request"}), 400

    short_id = cluster_id.split('-')[0]
    filename = f'hosts_{short_id}.json'
    data = load_fixture_page(filename, page)
    if data is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(data)


@app.route('/api/clustermgmt/v4.0/config/clusters')
def clusters():
    """Clusters endpoint (paginated)."""
    page = int(request.args.get('$page', 0))
    data = load_fixture_page('clusters.json', page)
    if data is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(data)


@app.route('/api/prism/v4.0/config/categories')
def categories():
    """Categories endpoint (paginated)."""
    page = int(request.args.get('$page', 0))
    data = load_fixture_page('categories.json', page)
    if data is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(data)


@app.route('/api/vmm/v4.0/ahv/stats/vms')
def vm_stats():
    """VM stats endpoint (paginated)."""
    page = int(request.args.get('$page', 0))
    data = load_fixture_page('vms_stats.json', page)
    if data is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(data)


@app.route('/api/vmm/v4.0/ahv/config/vms')
def vm_config():
    """VM config endpoint (paginated)."""
    page = int(request.args.get('$page', 0))
    data = load_fixture_page('vms.json', page)
    if data is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(data)


@app.route('/api/monitoring/v4.0/serviceability/events')
def events():
    """Events endpoint (paginated with time filtering)."""
    page = int(request.args.get('$page', 0))
    data = load_fixture_page('events.json', page)
    if data is None:
        return jsonify({"error": "Not found"}), 404

    filter_param = request.args.get('$filter', '')
    data = apply_time_filter(data, filter_param, 'creationTime')
    return jsonify(data)


@app.route('/api/monitoring/v4.0/serviceability/audits')
def audits():
    """Audits endpoint (paginated with time filtering)."""
    page = int(request.args.get('$page', 0))
    data = load_fixture_page('audits.json', page)
    if data is None:
        return jsonify({"error": "Not found"}), 404

    filter_param = request.args.get('$filter', '')
    data = apply_time_filter(data, filter_param, 'creationTime')
    return jsonify(data)


@app.route('/api/monitoring/v4.0/serviceability/alerts')
@app.route('/api/monitoring/v4.2/serviceability/alerts')
def alerts():
    """Alerts endpoint (paginated with time filtering)."""
    page = int(request.args.get('$page', 0))
    data = load_fixture_page('alerts.json', page)
    if data is None:
        return jsonify({"error": "Not found"}), 404

    filter_param = request.args.get('$filter', '')
    data = apply_time_filter(data, filter_param, 'creationTime')
    return jsonify(data)


@app.route('/api/prism/v4.0/config/tasks')
def tasks():
    """Tasks endpoint (paginated with time filtering)."""
    page = int(request.args.get('$page', 0))
    data = load_fixture_page('tasks.json', page)
    if data is None:
        return jsonify({"error": "Not found"}), 404

    filter_param = request.args.get('$filter', '')
    data = apply_time_filter(data, filter_param, 'createdTime')
    return jsonify(data)


if __name__ == '__main__':
    print("Starting Nutanix mock API server")
    print(f"Fixtures directory: {FIXTURES_DIR}")
    print("Listening on http://0.0.0.0:9440")
    app.run(host='0.0.0.0', port=9440, debug=False)
