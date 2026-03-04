# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

from datadog_checks.base.utils.tagging import tagger

POD_UID = 'aabbccdd-1234-5678-abcd-ef0123456789'
K8S_TAGS = ['pod_name:my-pod', 'kube_namespace:default', 'kube_deployment:my-app']


def test_sandbox_tags_include_only_sandbox_id_without_cri(make_check):
    assert make_check()._get_sandbox_tags('my-sandbox') == ['sandbox_id:my-sandbox']


def test_sandbox_tags_include_k8s_tags_when_cri_resolves_pod_uid(make_check):
    tagger.set_tags({'kubernetes_pod_uid://' + POD_UID: K8S_TAGS})
    check = make_check()
    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = POD_UID
    check._cri_client = mock_cri

    tags = check._get_sandbox_tags('my-sandbox')

    assert tags == ['sandbox_id:my-sandbox'] + K8S_TAGS
    mock_cri.get_pod_uid.assert_called_once_with('my-sandbox')


def test_sandbox_tags_include_only_sandbox_id_when_cri_returns_no_pod_uid(make_check):
    check = make_check()
    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = None
    check._cri_client = mock_cri

    assert check._get_sandbox_tags('my-sandbox') == ['sandbox_id:my-sandbox']


def test_pod_uid_is_cached_after_first_cri_lookup(make_check):
    """The CRI is queried only once per sandbox; subsequent calls use the cache."""
    check = make_check()
    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = POD_UID
    check._cri_client = mock_cri

    check._get_pod_uid('sandbox-1')
    check._get_pod_uid('sandbox-1')

    mock_cri.get_pod_uid.assert_called_once_with('sandbox-1')
