# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.vault import Vault

pytestmark = pytest.mark.unit


def test_client_token_path_leaves_api_client_intact(tmp_path):
    """Only the metrics scraper needs the token, since /sys/leader and /sys/health are unauthenticated.

    Rebuilding the check's client attaches a token handler that treats 429, the standby state, as an auth failure.
    """
    token_file = tmp_path / 'token'
    token_file.write_text('vault-token')
    instance = {
        'api_url': 'http://localhost:8200/v1',
        'client_token_path': str(token_file),
        'use_openmetrics': True,
    }

    check = Vault(Vault.CHECK_NAME, {}, [instance])
    api_client = check.http

    check.run_check_initializations()

    assert check.http is api_client
    assert check.scrapers[check._metrics_url].http is not api_client
