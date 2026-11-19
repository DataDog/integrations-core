# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path

import pytest

from datadog_checks.dev.fs import get_here

from .common import INSTANCE, SERVER_ROOT, fake_response


@pytest.fixture
def instance():
    return INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    yield INSTANCE


def get_json_value_from_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def parse_fixture_params(segments):
    """Turn `key=value` path segments into the `params` mapping the check sends."""
    params = {}
    for segment in segments:
        key, value = segment.split('=', 1)
        params[key] = int(value) if value.isdigit() else value
    return params


def register_fixture_tree(fake_http):
    """Serve every `fixtures/GET/<path>[/<key>=<value>...]/response.json` file at `<path>`.

    Requests to a fixture URL with query parameters that have no matching file get a 404, as a server would.
    """
    root = Path(get_here()) / 'fixtures' / 'GET'
    for file in sorted(root.rglob('response.json')):
        segments = file.parent.relative_to(root).parts
        path_segments = [segment for segment in segments if '=' not in segment]
        params = parse_fixture_params(segment for segment in segments if '=' in segment)
        url = f"{SERVER_ROOT}/{'/'.join(path_segments)}"
        if params:
            fake_http.register_response('GET', url, fake_response(status_code=404))
        fake_http.register_response(
            'GET',
            url,
            fake_response(json_data=get_json_value_from_file(file)),
            match_options={'params': params} if params else None,
        )


@pytest.fixture
def mock_http_get(request, fake_http):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.pop('http_error', {})

    register_fixture_tree(fake_http)
    # Registered last so they take precedence over the fixture tree, whatever the query parameters.
    for path, response in http_error.items():
        fake_http.register_response('GET', f'{SERVER_ROOT}{path}', response)
    return fake_http
