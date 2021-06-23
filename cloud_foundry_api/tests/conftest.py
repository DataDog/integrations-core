# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import pytest

from .constants import HERE


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {
        "api_url": "https://api.sys.domain.com",
        "client_id": "client_id",
        "client_secret": "client_secret",
        "tags": ["foo:bar"],
        "event_filter": ["audit1", "audit2"],
        "results_per_page": 45,
    }


@pytest.fixture
def instance_defaults():
    return {
        "api_url": "https://api.sys.domain.com",
        "client_id": "client_id",
        "client_secret": "client_secret",
    }


@pytest.fixture()
def events_v3_p0():
    """
    Returns raw events from API v3
    """
    with open(os.path.join(HERE, 'fixtures', 'events_v3_p0.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def events_v3_p1():
    """
    Returns raw events from API v3
    """
    with open(os.path.join(HERE, 'fixtures', 'events_v3_p1.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def events_v3_p2():
    """
    Returns raw events from API v3
    """
    with open(os.path.join(HERE, 'fixtures', 'events_v3_p2.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def orgs_v2_p1():
    """
    Returns raw orgs from API v2
    """
    with open(os.path.join(HERE, 'fixtures', 'orgs_v2_p1.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def orgs_v2_p2():
    """
    Returns raw orgs from API v2
    """
    with open(os.path.join(HERE, 'fixtures', 'orgs_v2_p2.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def orgs_v3_p1():
    """
    Returns raw orgs from API v3
    """
    with open(os.path.join(HERE, 'fixtures', 'orgs_v3_p1.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def orgs_v3_p2():
    """
    Returns raw orgs from API v3
    """
    with open(os.path.join(HERE, 'fixtures', 'orgs_v3_p2.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def spaces_v2_p1():
    """
    Returns raw spaces from API v2
    """
    with open(os.path.join(HERE, 'fixtures', 'spaces_v2_p1.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def spaces_v2_p2():
    """
    Returns raw spaces from API v2
    """
    with open(os.path.join(HERE, 'fixtures', 'spaces_v2_p2.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def spaces_v3_p1():
    """
    Returns raw spaces from API v3
    """
    with open(os.path.join(HERE, 'fixtures', 'spaces_v3_p1.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def spaces_v3_p2():
    """
    Returns raw spaces from API v3
    """
    with open(os.path.join(HERE, 'fixtures', 'spaces_v3_p2.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def space_v3():
    """
    Returns raw space from API v3
    """
    with open(os.path.join(HERE, 'fixtures', 'space_v3.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def space_v2():
    """
    Returns raw space from API v2
    """
    with open(os.path.join(HERE, 'fixtures', 'space_v2.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def org_v3():
    """
    Returns raw org from API v3
    """
    with open(os.path.join(HERE, 'fixtures', 'org_v3.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def org_v2():
    """
    Returns raw org from API v2
    """
    with open(os.path.join(HERE, 'fixtures', 'org_v2.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def dd_events():
    """
    Returns a dict of formatted events ready to send to Datadog
    """
    with open(os.path.join(HERE, 'fixtures', 'dd_events.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def oauth_token():
    """
    Returns the response from the UAA with the oauth_token
    """
    with open(os.path.join(HERE, 'fixtures', 'oauth_token.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def event_v2():
    """
    Returns a single v2 event
    """
    with open(os.path.join(HERE, 'fixtures', 'event_v2.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def event_v3():
    """
    Returns a single v3 event
    """
    with open(os.path.join(HERE, 'fixtures', 'event_v3.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def api_info_v3():
    """
    Returns API info with recent enough v3
    """
    with open(os.path.join(HERE, 'fixtures', 'api_info_v3.json')) as f:
        return json.loads(f.read())


@pytest.fixture()
def api_info_v2():
    """
    Returns API info without recent enough v3
    """
    with open(os.path.join(HERE, 'fixtures', 'api_info_v2.json')) as f:
        return json.loads(f.read())
