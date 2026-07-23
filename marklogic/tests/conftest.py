# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import http.client
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Generator  # noqa: F401

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor

from .common import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    API_URL,
    CHECK_CONFIG,
    HERE,
    MANAGE_ADMIN_USERNAME,
    MANAGE_USER_USERNAME,
    MARKLOGIC_VERSION,
    PASSWORD,
)


class HttpResponse:
    def __init__(self, url: str, status_code: int, reason: str, content: bytes) -> None:
        self.url = url
        self.status_code = status_code
        self.reason = reason or http.client.responses.get(status_code, '')
        self.content = content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise urllib.error.HTTPError(self.url, self.status_code, self.reason, http.client.HTTPMessage(), None)


def http_request(
    url: str,
    method: str = 'GET',
    *,
    data: dict[str, str] | str | bytes | None = None,
    headers: dict[str, str] | None = None,
    digest_auth: tuple[str, str] | None = None,
) -> HttpResponse:
    request_headers = dict(headers or {})
    body = None
    if isinstance(data, dict):
        body = urllib.parse.urlencode(data).encode('utf-8')
    elif isinstance(data, str):
        body = data.encode('utf-8')
    elif data is not None:
        body = data

    req = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    opener = urllib.request.build_opener()
    if digest_auth is not None:
        username, password = digest_auth
        password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(None, url, username, password)
        opener = urllib.request.build_opener(urllib.request.HTTPDigestAuthHandler(password_manager))

    try:
        with opener.open(req) as response:
            return HttpResponse(url, response.getcode(), response.reason, response.read())
    except urllib.error.HTTPError as error:
        return HttpResponse(url, error.code, error.reason, error.read())


@pytest.fixture(scope="session")
def dd_environment():
    # type: () -> Generator[Dict[str, Any], None, None]

    # Standalone
    compose_file = os.path.join(HERE, 'compose', 'standalone/docker-compose.yml')

    if MARKLOGIC_VERSION.startswith("9."):
        conditions = [
            CheckDockerLogs(compose_file, 'Deleted', wait=5),
        ]
    else:
        conditions = [
            CheckDockerLogs(compose_file, 'Cluster config complete, marking this node as ready.', wait=5),
        ]

    conditions.append(WaitFor(setup_admin_user))
    conditions.append(WaitFor(setup_datadog_users))

    with docker_run(
        compose_file=compose_file,
        conditions=conditions,
    ):
        yield CHECK_CONFIG


def setup_admin_user():
    # type: () -> None
    # From https://docs.marklogic.com/10.0/guide/admin-api/cluster
    # Reset admin user password (useful for cluster setup)
    http_request(
        'http://localhost:8001/admin/v1/instance-admin',
        method='POST',
        data={
            "admin-username": ADMIN_USERNAME,
            "admin-password": ADMIN_PASSWORD,
            "wallet-password": ADMIN_PASSWORD,
            "realm": "public",
        },
        headers={"Content-type": "application/x-www-form-urlencoded"},
    )

    r = http_request('{}/manage/v2'.format(API_URL), digest_auth=(ADMIN_USERNAME, ADMIN_PASSWORD))

    r.raise_for_status()


def setup_datadog_users():
    # type: () -> None
    # Create datadog users with the admin account
    r = http_request(
        '{}/manage/v2/users'.format(API_URL),
        method='POST',
        headers={'Content-Type': 'application/json'},
        data='{{"user-name": "{}", "password": "{}", "roles": {{"role": "manage-user"}}}}'.format(
            MANAGE_USER_USERNAME, PASSWORD
        ),
        digest_auth=(ADMIN_USERNAME, ADMIN_PASSWORD),
    )

    r.raise_for_status()

    r = http_request(
        '{}/manage/v2/users'.format(API_URL),
        method='POST',
        headers={'Content-Type': 'application/json'},
        data='{{"user-name": "{}", "password": "{}", "roles": {{"role": "manage-admin"}}}}'.format(
            MANAGE_ADMIN_USERNAME, PASSWORD
        ),
        digest_auth=(ADMIN_USERNAME, ADMIN_PASSWORD),
    )

    r.raise_for_status()
