# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from . import kube

pytestmark = pytest.mark.unit

MANIFEST_URL = 'https://github.com/kubernetes-sigs/kueue/releases/download/v0.18.0/manifests.yaml'
MANIFEST = b'apiVersion: v1\nkind: Namespace\nmetadata:\n  name: kueue-system\n'


def http_response(status: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = MANIFEST_URL
    response._content = MANIFEST
    response._content_consumed = True
    return response


@pytest.mark.parametrize('failure', [500, 503, 408, 429, requests.ConnectionError(), requests.Timeout()])
def test_fetch_manifest_recovers_from_transient_failures(monkeypatch: pytest.MonkeyPatch, failure: int | Exception):
    failure = http_response(failure) if isinstance(failure, int) else failure
    get = Mock(side_effect=[failure] * 4 + [http_response(200)])
    monkeypatch.setattr(kube.requests, 'get', get)
    sleeps = []
    monkeypatch.setattr(kube.fetch_manifest.retry, 'sleep', sleeps.append)

    assert kube.fetch_manifest(MANIFEST_URL) == MANIFEST
    assert get.call_count == 5
    get.assert_called_with(MANIFEST_URL, timeout=(10, 30))
    assert sleeps == [2, 4, 8, 16]


@pytest.mark.parametrize('status', [401, 403, 404])
def test_fetch_manifest_does_not_retry_permanent_errors(monkeypatch: pytest.MonkeyPatch, status: int):
    get = Mock(return_value=http_response(status))
    monkeypatch.setattr(kube.requests, 'get', get)
    sleep = Mock()
    monkeypatch.setattr(kube.fetch_manifest.retry, 'sleep', sleep)

    with pytest.raises(requests.HTTPError) as error:
        kube.fetch_manifest(MANIFEST_URL)

    assert error.value.response.status_code == status
    get.assert_called_once()
    sleep.assert_not_called()


def test_fetch_manifest_stops_after_five_attempts(monkeypatch: pytest.MonkeyPatch):
    get = Mock(return_value=http_response(500))
    monkeypatch.setattr(kube.requests, 'get', get)
    sleeps = []
    monkeypatch.setattr(kube.fetch_manifest.retry, 'sleep', sleeps.append)

    with pytest.raises(requests.HTTPError) as error:
        kube.fetch_manifest(MANIFEST_URL)

    assert error.value.response.status_code == 500
    assert get.call_count == 5
    assert sleeps == [2, 4, 8, 16]


@pytest.mark.parametrize('apply_fails', [False, True])
def test_apply_remote_manifest_applies_download_once_and_cleans_up(monkeypatch: pytest.MonkeyPatch, apply_fails: bool):
    get = Mock(return_value=http_response(200))
    monkeypatch.setattr(kube.requests, 'get', get)
    paths = []
    env = {'KUBECONFIG': 'test-kubeconfig'}

    def apply(args: list[str], env: dict[str, str] | None = None) -> None:
        assert args[:3] == ['apply', '--server-side', '-f']
        path = Path(args[3])
        paths.append(path)
        assert path.read_bytes() == MANIFEST
        if apply_fails:
            raise RuntimeError('apply failed')

    kubectl = Mock(side_effect=apply)
    monkeypatch.setattr(kube, 'kubectl', kubectl)

    if apply_fails:
        with pytest.raises(RuntimeError, match='apply failed'):
            kube.apply_remote_manifest(MANIFEST_URL, env=env)
    else:
        kube.apply_remote_manifest(MANIFEST_URL, env=env)

    get.assert_called_once()
    kubectl.assert_called_once_with(['apply', '--server-side', '-f', str(paths[0])], env=env)
    assert not paths[0].exists()
