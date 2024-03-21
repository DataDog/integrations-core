# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from datadog_checks.dev import get_here
from datadog_checks.istio.constants import BLACKLIST_LABELS

HERE = get_here()


def get_fixture_path(version, filename):
    return os.path.join(HERE, 'fixtures', version, filename)


def get_response(version, filename):
    metrics_file_path = get_fixture_path(version, filename)
    with open(metrics_file_path, 'r') as f:
        response = f.read()
    return response


def _assert_tags_excluded(aggregator, addl_exclusion, exclude_connectionid):
    """
    Test excluded labels. ConnectionID is only excluded in the v1 version of the check.
    """
    fail = 0
    if exclude_connectionid:
        addl_exclusion = BLACKLIST_LABELS + addl_exclusion

    for _, stubs in aggregator._metrics.items():
        for stub in stubs:
            for tag in stub.tags:
                for excluded_tag in addl_exclusion:
                    if tag.startswith(excluded_tag + ':'):
                        fail += 1
    assert fail == 0
    aggregator.assert_all_metrics_covered()
