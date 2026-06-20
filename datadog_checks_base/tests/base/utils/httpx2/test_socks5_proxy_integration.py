# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.httpx2 import HTTPX2Wrapper
from datadog_checks.dev.ci import running_on_ci, running_on_windows_ci

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI'),
    pytest.mark.skipif(running_on_ci(), reason='Test is failing on CI'),
]


def test_socks5_proxy(socks5_proxy):
    instance = {'proxy': {'http': 'socks5h://{}'.format(socks5_proxy)}}
    init_config = {}
    with HTTPX2Wrapper(instance, init_config) as http:
        with http.get('http://www.google.com') as resp:
            assert resp.status_code == 200
        with http.get('http://nginx') as resp:
            assert resp.ok
