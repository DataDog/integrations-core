# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from datetime import datetime

import mock

from datadog_checks.base.checks.kubelet_base.base import KubeletBase, urljoin
from datadog_checks.base.utils.date import UTC

HERE = os.path.abspath(os.path.dirname(__file__))


def mock_from_file(fname):
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return f.read()


class MockStreamResponse:
    """
    Mocks raw contents of a stream request for the podlist get
    """

    def __init__(self, filename):
        self.filename = filename

    @property
    def raw(self):
        return open(os.path.join(HERE, 'fixtures', self.filename))

    def json(self):
        with open(os.path.join(HERE, 'fixtures', self.filename)) as f:
            return json.load(f)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_retrieve_pod_list_success(monkeypatch):
    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = "dummyurl"
    monkeypatch.setattr(
        check,
        'perform_kubelet_query',
        mock.Mock(return_value=MockStreamResponse('kubelet_base/pod_list_raw.dat')),
    )
    monkeypatch.setattr(check, 'compute_pod_expiration_datetime', mock.Mock(return_value=None))

    retrieved = check.retrieve_pod_list()
    expected = json.loads(mock_from_file("kubelet_base/pod_list_raw.json"))
    assert json.dumps(retrieved, sort_keys=True) == json.dumps(expected, sort_keys=True)


def test_retrieved_pod_list_failure(monkeypatch):
    def mock_perform_kubelet_query(s, stream=False):
        raise Exception("network error")

    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = "dummyurl"
    monkeypatch.setattr(check, 'perform_kubelet_query', mock_perform_kubelet_query)

    retrieved = check.retrieve_pod_list()
    assert retrieved == {}


def test_compute_pod_expiration_datetime(monkeypatch):
    # Invalid input
    with mock.patch("datadog_checks.base.checks.kubelet_base.base.get_config", return_value="") as p:
        assert KubeletBase.compute_pod_expiration_datetime() is None
        p.assert_called_with("kubernetes_pod_expiration_duration")

    with mock.patch("datadog_checks.base.checks.kubelet_base.base.get_config", return_value="invalid"):
        assert KubeletBase.compute_pod_expiration_datetime() is None

    # Disabled
    with mock.patch("datadog_checks.base.checks.kubelet_base.base.get_config", return_value="0"):
        assert KubeletBase.compute_pod_expiration_datetime() is None

    # Set to 15 minutes
    with mock.patch("datadog_checks.base.checks.kubelet_base.base.get_config", return_value="900"):
        expire = KubeletBase.compute_pod_expiration_datetime()
        assert expire is not None
        now = datetime.utcnow().replace(tzinfo=UTC)
        assert abs((now - expire).seconds - 60 * 15) < 2


def test_urljoin():
    base = 'https://www.example.com'
    base_with_slash = base + '/'
    one_level = 'https://www.example.com/test'
    two_levels = one_level + '/another'

    result = urljoin(base, 'test')
    assert result == one_level
    result = urljoin(base, '/test')
    assert result == one_level
    result = urljoin(base, '/test/')
    assert result == one_level

    result = urljoin(base_with_slash, 'test')
    assert result == one_level
    result = urljoin(base_with_slash, '/test')
    assert result == one_level
    result = urljoin(base_with_slash, '/test/')
    assert result == one_level

    result = urljoin(base, 'test', 'another')
    assert result == two_levels
    result = urljoin(base, 'test/', 'another/')
    assert result == two_levels
    result = urljoin(base, '/test/', '/another/')
    assert result == two_levels
