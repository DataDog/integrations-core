# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock


def test_discover_sandboxes_returns_empty_when_storage_paths_missing(make_check):
    check = make_check()
    with mock.patch('os.path.exists', return_value=False):
        assert check._discover_sandboxes() == {}


def test_discover_sandboxes_returns_sandbox_to_socket_mapping(make_check, make_sandbox_mocks):
    sandbox_id = 'abc123'
    check = make_check()
    mock_exists, mock_listdir, mock_isdir, socket_path = make_sandbox_mocks(sandbox_id)

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
    ):
        result = check._discover_sandboxes()

    assert result == {sandbox_id: socket_path}


def test_discover_sandboxes_skips_sandbox_without_socket(make_check):
    """A sandbox directory without shim-monitor.sock is silently excluded."""
    sandbox_id = 'no-socket'
    storage_path = '/run/vc/sbs'
    check = make_check()

    with (
        mock.patch('os.path.exists', side_effect=lambda p: p == storage_path),
        mock.patch('os.listdir', return_value=[sandbox_id]),
        mock.patch('os.path.isdir', return_value=True),
    ):
        result = check._discover_sandboxes()

    assert result == {}


def test_discover_sandboxes_uses_custom_storage_path(make_check, make_sandbox_mocks):
    """sandbox_storage_paths in the instance config overrides the class default."""
    sandbox_id = 'custom-sandbox'
    custom_path = '/custom/kata/sbs'
    check = make_check({'sandbox_storage_paths': [custom_path]})
    mock_exists, mock_listdir, mock_isdir, socket_path = make_sandbox_mocks(sandbox_id, storage_path=custom_path)

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
    ):
        result = check._discover_sandboxes()

    assert result == {sandbox_id: socket_path}


def test_discover_sandboxes_logs_and_continues_on_os_error(make_check):
    """An OSError while scanning a storage path is absorbed; other paths are still processed."""
    check = make_check()

    with (
        mock.patch('os.path.exists', return_value=True),
        mock.patch('os.listdir', side_effect=OSError('permission denied')),
    ):
        result = check._discover_sandboxes()

    assert result == {}


def test_refresh_scrapers_emits_zero_shim_count_when_no_sandboxes(aggregator, make_check):
    check = make_check()

    with (
        mock.patch('os.path.exists', return_value=False),
        mock.patch.object(check, 'configure_scrapers'),
    ):
        check.refresh_scrapers()

    aggregator.assert_metric('kata.running_shim_count', value=0)


def test_refresh_scrapers_emits_shim_count_equal_to_discovered_sandboxes(aggregator, make_check, make_sandbox_mocks):
    sandbox_id = 'test-sandbox'
    check = make_check()
    mock_exists, mock_listdir, mock_isdir, _ = make_sandbox_mocks(sandbox_id)

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch.object(check, 'configure_scrapers'),
    ):
        check.refresh_scrapers()

    aggregator.assert_metric('kata.running_shim_count', value=1)
    assert len(check.scraper_configs) == 1


def test_pod_uid_cache_entry_is_evicted_when_sandbox_disappears(aggregator, make_check, make_sandbox_mocks):
    """Cache entries for sandboxes that no longer exist are removed on the next refresh."""
    sandbox_id = 'evicted-sandbox'
    check = make_check()
    mock_exists, mock_listdir, mock_isdir, _ = make_sandbox_mocks(sandbox_id)

    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = 'some-pod-uid'
    check._cri_client = mock_cri

    # First refresh — sandbox present, cache populated via _build_scraper_config → _get_pod_uid.
    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch.object(check, 'configure_scrapers'),
    ):
        check.refresh_scrapers()

    assert sandbox_id in check._pod_uid_cache

    # Second refresh — sandbox gone, cache entry evicted.
    with (
        mock.patch('os.path.exists', return_value=False),
        mock.patch.object(check, 'configure_scrapers'),
    ):
        check.refresh_scrapers()

    assert sandbox_id not in check._pod_uid_cache
