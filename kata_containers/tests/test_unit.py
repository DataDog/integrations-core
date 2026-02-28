# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, Dict  # noqa: F401
from unittest import mock

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.utils.tagging import tagger
from datadog_checks.kata_containers import KataContainersCheck

POD_UID = 'aabbccdd-1234-5678-abcd-ef0123456789'
K8S_TAGS = ['pod_name:my-pod', 'kube_namespace:default', 'kube_deployment:my-app']


@pytest.fixture(autouse=True)
def reset_tagger():
    tagger.reset()
    yield
    tagger.reset()


def _make_check(instance=None):
    return KataContainersCheck('kata_containers', {}, [instance or {}])


def _make_sandbox_mocks(sandbox_id: str, storage_path: str = '/run/vc/sbs'):
    socket_path = f'{storage_path}/{sandbox_id}/shim-monitor.sock'

    def mock_exists(path):
        return path in [storage_path, socket_path]

    def mock_listdir(path):
        return [sandbox_id] if path == storage_path else []

    def mock_isdir(path):
        return path == f'{storage_path}/{sandbox_id}'

    return mock_exists, mock_listdir, mock_isdir, socket_path


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def test_discover_sandboxes_empty_when_paths_missing(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = _make_check()
    with mock.patch('os.path.exists', return_value=False):
        assert check._discover_sandboxes() == {}


def test_discover_sandboxes_finds_socket(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    sandbox_id = 'abc123'
    check = _make_check()
    mock_exists, mock_listdir, mock_isdir, socket_path = _make_sandbox_mocks(sandbox_id)

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
    ):
        result = check._discover_sandboxes()

    assert result == {sandbox_id: socket_path}


# ---------------------------------------------------------------------------
# Tag enrichment
# ---------------------------------------------------------------------------


def test_get_sandbox_tags_no_cri(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = _make_check()
    # No CRI client → only sandbox_id tag
    assert check._get_sandbox_tags('my-sandbox') == ['sandbox_id:my-sandbox']


def test_get_sandbox_tags_with_cri_and_tagger(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = _make_check()
    tagger.set_tags({'kubernetes_pod_uid://' + POD_UID: K8S_TAGS})

    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = POD_UID
    check._cri_client = mock_cri

    tags = check._get_sandbox_tags('my-sandbox')
    assert tags == ['sandbox_id:my-sandbox'] + K8S_TAGS
    mock_cri.get_pod_uid.assert_called_once_with('my-sandbox')


def test_get_sandbox_tags_cri_returns_none(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = _make_check()
    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = None
    check._cri_client = mock_cri

    assert check._get_sandbox_tags('my-sandbox') == ['sandbox_id:my-sandbox']


# ---------------------------------------------------------------------------
# Scraper config builder
# ---------------------------------------------------------------------------


def test_build_scraper_config_endpoint(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = _make_check()
    socket_path = '/run/vc/sbs/abc123/shim-monitor.sock'
    config = check._build_scraper_config('abc123', socket_path)

    assert config['openmetrics_endpoint'] == 'unix:///run/vc/sbs/abc123/shim-monitor.sock/metrics'


def test_build_scraper_config_default_rename_labels(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = _make_check()
    config = check._build_scraper_config('abc123', '/run/vc/sbs/abc123/shim-monitor.sock')

    # version→go_version must always be present
    assert config['rename_labels'].get('version') == 'go_version'


def test_build_scraper_config_user_rename_labels_merged(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = _make_check({'rename_labels': {'my_label': 'my_renamed'}})
    config = check._build_scraper_config('abc123', '/run/vc/sbs/abc123/shim-monitor.sock')

    # Both the default and the user addition must be present
    assert config['rename_labels'].get('version') == 'go_version'
    assert config['rename_labels'].get('my_label') == 'my_renamed'


def test_build_scraper_config_tags_include_sandbox_id(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = _make_check({'tags': ['env:prod']})
    config = check._build_scraper_config('abc123', '/run/vc/sbs/abc123/shim-monitor.sock')

    assert 'sandbox_id:abc123' in config['tags']
    assert 'env:prod' in config['tags']


# ---------------------------------------------------------------------------
# refresh_scrapers / running_shim_count
# ---------------------------------------------------------------------------


def test_refresh_scrapers_no_sandboxes(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    check = _make_check()

    with (
        mock.patch('os.path.exists', return_value=False),
        mock.patch.object(check, 'configure_scrapers'),
    ):
        check.refresh_scrapers()

    aggregator.assert_metric('kata.running_shim_count', value=0)


def test_refresh_scrapers_counts_sandboxes(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    sandbox_id = 'test-sandbox'
    check = _make_check()
    mock_exists, mock_listdir, mock_isdir, _ = _make_sandbox_mocks(sandbox_id)

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch.object(check, 'configure_scrapers'),
    ):
        check.refresh_scrapers()

    aggregator.assert_metric('kata.running_shim_count', value=1)
    assert len(check.scraper_configs) == 1


# ---------------------------------------------------------------------------
# Pod UID cache
# ---------------------------------------------------------------------------


def test_pod_uid_cache_hit(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = _make_check()
    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = POD_UID
    check._cri_client = mock_cri

    check._get_pod_uid('sandbox-1')
    check._get_pod_uid('sandbox-1')

    mock_cri.get_pod_uid.assert_called_once_with('sandbox-1')


def test_pod_uid_cache_eviction(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    sandbox_id = 'evicted-sandbox'
    check = _make_check()
    mock_exists, mock_listdir, mock_isdir, _ = _make_sandbox_mocks(sandbox_id)

    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = POD_UID
    check._cri_client = mock_cri

    # First refresh — sandbox present, cache populated.
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


# ---------------------------------------------------------------------------
# CRI client init
# ---------------------------------------------------------------------------


def test_cri_init_skipped_when_grpc_unavailable(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = _make_check()
    with mock.patch('datadog_checks.kata_containers.check.GRPC_AVAILABLE', False):
        check._init_cri_client()
    assert check._cri_client is None


def test_cri_init_uses_config_socket_path(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = _make_check({'cri_socket_path': '/run/custom/cri.sock'})
    mock_cri_class = mock.Mock(return_value=mock.Mock())

    with mock.patch('datadog_checks.kata_containers.check.CRIClient', mock_cri_class):
        check._init_cri_client()

    mock_cri_class.assert_called_once_with(socket_path='/run/custom/cri.sock')
