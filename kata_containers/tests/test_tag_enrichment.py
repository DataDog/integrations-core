# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.tagging import tagger

K8S_TAGS = ['pod_name:my-pod', 'kube_namespace:default', 'kube_deployment:my-app']


def test_sandbox_tags_include_sandbox_id(make_check):
    assert make_check()._get_sandbox_tags('my-sandbox') == ['sandbox_id:my-sandbox']


def test_sandbox_tags_include_k8s_tags_when_tagger_has_container_tags(make_check):
    tagger.set_tags({'sandbox_id://my-sandbox': K8S_TAGS})

    tags = make_check()._get_sandbox_tags('my-sandbox')

    assert tags == ['sandbox_id:my-sandbox'] + K8S_TAGS


def test_sandbox_tags_include_only_sandbox_id_when_tagger_has_no_container_tags(make_check):
    assert make_check()._get_sandbox_tags('my-sandbox') == ['sandbox_id:my-sandbox']
