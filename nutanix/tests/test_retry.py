# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from unittest.mock import Mock

import pytest
from requests import HTTPError, Response

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


def test_retry_on_rate_limit_success_no_retry(dd_run_check, aggregator, mock_instance, mocker):
    """Test successful request without needing retries."""
    mock_response = Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"test": "data"}}
    mock_response.raise_for_status = Mock()
    mock_response.content = b'{"data": {"test": "data"}}'

    mock_get = mocker.patch('requests.Session.get', return_value=mock_response)

    check = NutanixCheck('nutanix', {}, [mock_instance])
    result = check._get_request_data("api/test")

    assert result == {"test": "data"}
    assert mock_get.call_count == 1
    aggregator.assert_metric("nutanix.api.rate_limited", count=0)


def test_retry_on_rate_limit_429_then_success(dd_run_check, aggregator, mock_instance, mocker):
    """Test retry on 429 rate limit, then success."""
    # First response: 429 rate limited
    mock_response_429 = Mock(spec=Response)
    mock_response_429.status_code = 429
    mock_response_429.raise_for_status.side_effect = HTTPError(response=mock_response_429)
    mock_response_429.content = b''

    # Second response: success
    mock_response_200 = Mock(spec=Response)
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {"data": {"test": "data"}}
    mock_response_200.raise_for_status = Mock()
    mock_response_200.content = b'{"data": {"test": "data"}}'

    mock_get = mocker.patch('requests.Session.get', side_effect=[mock_response_429, mock_response_200])
    mock_sleep = mocker.patch('time.sleep')

    check = NutanixCheck('nutanix', {}, [mock_instance])
    result = check._get_request_data("api/test")

    assert result == {"test": "data"}
    assert mock_get.call_count == 2
    assert mock_sleep.call_count == 1

    # First retry: base * 2^1 + jitter = 2 to 3
    sleep_time = mock_sleep.call_args[0][0]
    assert 2.0 <= sleep_time <= 3.0

    aggregator.assert_metric("nutanix.api.rate_limited", value=1, tags=['nutanix', 'prism_central:10.0.0.197'])


def test_retry_on_rate_limit_max_retries_exceeded(dd_run_check, aggregator, mock_instance, mocker):
    """Test max retries exceeded with continuous 429 responses."""
    mock_response_429 = Mock(spec=Response)
    mock_response_429.status_code = 429
    mock_response_429.raise_for_status.side_effect = HTTPError(response=mock_response_429)
    mock_response_429.content = b''

    mock_get = mocker.patch('requests.Session.get', return_value=mock_response_429)
    mock_sleep = mocker.patch('time.sleep')

    # Set max_retries to 2 for faster test
    mock_instance['pc_max_retries'] = 2

    check = NutanixCheck('nutanix', {}, [mock_instance])

    with pytest.raises(HTTPError):
        check._get_request_data("api/test")

    # Initial request + 1 retry (range(1, 2)) = 2 total
    assert mock_get.call_count == 2
    assert mock_sleep.call_count == 1  # Sleep between retries (not after final failure)

    aggregator.assert_metric("nutanix.api.rate_limited", tags=['nutanix', 'prism_central:10.0.0.197'])


def test_retry_on_non_429_error_no_retry(dd_run_check, aggregator, mock_instance, mocker):
    """Test that non-429 HTTP errors are not retried."""
    # 500 Internal Server Error
    mock_response_500 = Mock(spec=Response)
    mock_response_500.status_code = 500
    mock_response_500.raise_for_status.side_effect = HTTPError(response=mock_response_500)
    mock_response_500.content = b''

    mock_get = mocker.patch('requests.Session.get', return_value=mock_response_500)
    mock_sleep = mocker.patch('time.sleep')

    check = NutanixCheck('nutanix', {}, [mock_instance])

    with pytest.raises(HTTPError):
        check._get_request_data("api/test")

    # Should only try once, no retries for non-429 errors
    assert mock_get.call_count == 1
    assert mock_sleep.call_count == 0

    aggregator.assert_metric("nutanix.api.rate_limited", count=0)


def test_retry_with_custom_config(dd_run_check, aggregator, mock_instance, mocker):
    """Test retry with custom configuration parameters."""
    # Configure custom retry parameters
    mock_instance['pc_max_retries'] = 5
    mock_instance['pc_base_backoff_seconds'] = 2
    mock_instance['pc_max_backoff_seconds'] = 10

    # First two responses: 429, then success
    mock_response_429 = Mock(spec=Response)
    mock_response_429.status_code = 429
    mock_response_429.raise_for_status.side_effect = HTTPError(response=mock_response_429)
    mock_response_429.content = b''

    mock_response_200 = Mock(spec=Response)
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {"data": {"test": "data"}}
    mock_response_200.raise_for_status = Mock()
    mock_response_200.content = b'{"data": {"test": "data"}}'

    mock_get = mocker.patch('requests.Session.get', side_effect=[mock_response_429, mock_response_200])
    mock_sleep = mocker.patch('time.sleep')

    check = NutanixCheck('nutanix', {}, [mock_instance])
    result = check._get_request_data("api/test")

    assert result == {"test": "data"}
    assert mock_get.call_count == 2

    # First retry: base * 2^1 + jitter = 4 to 5 (base=2)
    sleep_time = mock_sleep.call_args[0][0]
    assert 4.0 <= sleep_time <= 5.0


def test_retry_exponential_backoff(dd_run_check, aggregator, mock_instance, mocker):
    """Test exponential backoff calculation."""
    # Configure to allow 4 retries
    mock_instance['pc_max_retries'] = 4
    mock_instance['pc_base_backoff_seconds'] = 1
    mock_instance['pc_max_backoff_seconds'] = 20

    # Four 429 responses, then success
    mock_response_429 = Mock(spec=Response)
    mock_response_429.status_code = 429
    mock_response_429.raise_for_status.side_effect = HTTPError(response=mock_response_429)
    mock_response_429.content = b''

    mock_response_200 = Mock(spec=Response)
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {"data": {"test": "data"}}
    mock_response_200.raise_for_status = Mock()
    mock_response_200.content = b'{"data": {"test": "data"}}'

    mock_get = mocker.patch(
        'requests.Session.get', side_effect=[mock_response_429, mock_response_429, mock_response_429, mock_response_200]
    )
    mock_sleep = mocker.patch('time.sleep')

    check = NutanixCheck('nutanix', {}, [mock_instance])
    result = check._get_request_data("api/test")

    assert result == {"test": "data"}
    assert mock_get.call_count == 4
    assert mock_sleep.call_count == 3

    # Check exponential backoff pattern: base * 2^attempt + jitter (attempt starts at 1)
    sleep_times = [call[0][0] for call in mock_sleep.call_args_list]

    # attempt=1: 1 * 2^1 + jitter = 2 to 3
    assert 2.0 <= sleep_times[0] <= 3.0

    # attempt=2: 1 * 2^2 + jitter = 4 to 5
    assert 4.0 <= sleep_times[1] <= 5.0

    # attempt=3: 1 * 2^3 + jitter = 8 to 9
    assert 8.0 <= sleep_times[2] <= 9.0


def test_retry_disabled_with_zero_max_retries(dd_run_check, aggregator, mock_instance, mocker):
    """Test that setting max_retries to 0 disables retry logic."""
    mock_instance['pc_max_retries'] = 0

    mock_response_429 = Mock(spec=Response)
    mock_response_429.status_code = 429
    mock_response_429.raise_for_status.side_effect = HTTPError(response=mock_response_429)
    mock_response_429.content = b''

    mock_get = mocker.patch('requests.Session.get', return_value=mock_response_429)
    mock_sleep = mocker.patch('time.sleep')

    check = NutanixCheck('nutanix', {}, [mock_instance])

    with pytest.raises(HTTPError):
        check._get_request_data("api/test")

    # Should only try once when max_retries is 0
    assert mock_get.call_count == 1
    assert mock_sleep.call_count == 0

    # Loop never runs with max_retries=0 (clamped to 1), so no rate_limited metric is emitted
    aggregator.assert_metric("nutanix.api.rate_limited", count=0)


def test_health_check_with_retry(dd_run_check, aggregator, mock_instance, mocker):
    """Test health check endpoint uses retry logic."""
    # First response: 429 rate limited
    mock_response_429 = Mock(spec=Response)
    mock_response_429.status_code = 429
    mock_response_429.raise_for_status.side_effect = HTTPError(response=mock_response_429)
    mock_response_429.content = b''

    # Second response: success
    mock_response_200 = Mock(spec=Response)
    mock_response_200.status_code = 200
    mock_response_200.raise_for_status = Mock()
    mock_response_200.content = b''

    mock_get = mocker.patch('requests.Session.get', side_effect=[mock_response_429, mock_response_200])
    mock_sleep = mocker.patch('time.sleep')

    check = NutanixCheck('nutanix', {}, [mock_instance])
    result = check._check_health()

    assert result is True
    assert mock_get.call_count == 2
    assert mock_sleep.call_count == 1

    # Health check should report up after successful retry
    aggregator.assert_metric("nutanix.health.up", value=1, tags=['nutanix', 'prism_central:10.0.0.197'])
