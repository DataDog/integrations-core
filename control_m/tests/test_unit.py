# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from _pytest.monkeypatch import MonkeyPatch

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.control_m import ControlMCheck

FIXTURE_DIR = Path(__file__).parent / 'fixtures'


def test_check_can_connect(
    dd_run_check: Callable[[AgentCheck, bool], None],
    aggregator: AggregatorStub,
    instance: dict[str, Any],
    mock_http_response: Callable[..., Any],
) -> None:
    mock_http_response((FIXTURE_DIR / 'config_servers_response.txt').read_text())
    check = ControlMCheck('control_m', {}, [instance])
    dd_run_check(check)

    aggregator.assert_service_check('control_m.can_connect', status=AgentCheck.OK, count=1)
    aggregator.assert_metric(
        'control_m.can_connect',
        value=1,
        tags=['control_m_instance:https://example.com/automation-api', 'auth_method:static_token'],
        count=1,
    )
    aggregator.assert_all_metrics_covered()


def test_check_connectivity_failure_reports_critical(
    dd_run_check: Callable[[AgentCheck, bool], None],
    aggregator: AggregatorStub,
    instance: dict[str, Any],
    mock_http_response: Callable[..., Any],
) -> None:
    mock_http_response(status_code=500)
    check = ControlMCheck('control_m', {}, [instance])

    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check('control_m.can_connect', status=AgentCheck.CRITICAL, count=1)
    aggregator.assert_metric(
        'control_m.can_connect',
        value=0,
        tags=['control_m_instance:https://example.com/automation-api', 'auth_method:static_token'],
        count=1,
    )


def test_check_session_login_mode(
    dd_run_check: Callable[[AgentCheck, bool], None],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    instance = {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'control_m_username': 'workbench',
        'control_m_password': 'workbench',
    }
    check = ControlMCheck('control_m', {}, [instance])

    response = Mock()
    response.status_code = 200
    response.raise_for_status = Mock()
    response.json.return_value = [{'name': 'workbench', 'state': 'Up', 'version': '9.0.21.080'}]

    monkeypatch.setattr(check, '_ensure_token', Mock(side_effect=lambda: setattr(check, '_token', 'session-token')))
    monkeypatch.setattr(check, '_make_request', Mock(return_value=response))

    dd_run_check(check)

    aggregator.assert_service_check(
        'control_m.can_login',
        status=AgentCheck.OK,
        tags=['control_m_instance:https://example.com/automation-api', 'auth_method:session_login'],
        count=1,
    )
    aggregator.assert_service_check(
        'control_m.can_connect',
        status=AgentCheck.OK,
        tags=['control_m_instance:https://example.com/automation-api', 'auth_method:session_login'],
        count=1,
    )
    aggregator.assert_metric(
        'control_m.can_connect',
        value=1,
        tags=['control_m_instance:https://example.com/automation-api', 'auth_method:session_login'],
        count=1,
    )


def test_session_token_refresh_behavior() -> None:
    instance = {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'control_m_username': 'workbench',
        'control_m_password': 'workbench',
        'token_refresh_buffer_seconds': 300,
    }
    check = ControlMCheck('control_m', {}, [instance])
    check._login = Mock()
    check._token = 'existing-token'

    # Token has plenty of remaining lifetime; no refresh should occur.
    check._token_expiration = time.monotonic() + check._token_refresh_buffer + 10
    check._ensure_token()
    check._login.assert_not_called()

    # Token is within the refresh buffer; refresh should occur.
    check._token_expiration = time.monotonic() + check._token_refresh_buffer - 1
    check._ensure_token()
    check._login.assert_called_once()
