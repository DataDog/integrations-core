# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from datadog_checks.base.utils.genresources.redaction import apply_deny_list


def test_apply_deny_list_does_not_mutate_input():
    fields = {"spec": {"source": {"helm": {"valuesObject": "topsecret"}}}}
    apply_deny_list(fields, paths=["spec.source.helm.valuesObject"], annotation_keys=[])
    assert fields["spec"]["source"]["helm"]["valuesObject"] == "topsecret"
