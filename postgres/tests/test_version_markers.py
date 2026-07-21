# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import POSTGRES_VERSION
from .utils import (
    requires_over,
    requires_over_10,
    requires_over_11,
    requires_over_12,
    requires_over_13,
    requires_over_14,
    requires_over_15,
    requires_over_16,
    requires_over_17,
    requires_over_18,
    requires_under,
    requires_under_17,
)

pytestmark = pytest.mark.unit


def _condition_and_reason(marker):
    return marker.mark.args[0], marker.mark.kwargs['reason']


# Each alias must resolve to exactly the marker the old hand-written literal produced. The literals
# below are the pre-refactor definitions, inlined so the equality is visible to the reviewer.
def test_requires_over_aliases_match_old_literals():
    for version, alias in [
        (10, requires_over_10),
        (11, requires_over_11),
        (12, requires_over_12),
        (13, requires_over_13),
        (14, requires_over_14),
        (15, requires_over_15),
        (16, requires_over_16),
        (17, requires_over_17),
    ]:
        expected = pytest.mark.skipif(
            POSTGRES_VERSION is None or float(POSTGRES_VERSION) < version,
            reason=f'This test is for over {version} only (make sure POSTGRES_VERSION is set)',
        )
        assert _condition_and_reason(alias) == _condition_and_reason(expected)


def test_requires_under_17_alias_matches_old_literal():
    expected = pytest.mark.skipif(
        POSTGRES_VERSION is None or float(POSTGRES_VERSION) >= 17,
        reason='This test is for under 17 only (make sure POSTGRES_VERSION is set)',
    )
    assert _condition_and_reason(requires_under_17) == _condition_and_reason(expected)


def test_requires_over_18_added():
    expected = pytest.mark.skipif(
        POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 18,
        reason='This test is for over 18 only (make sure POSTGRES_VERSION is set)',
    )
    assert _condition_and_reason(requires_over_18) == _condition_and_reason(expected)


def test_factories_gate_on_version():
    assert requires_over(18).mark.args[0] == (POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 18)
    assert requires_under(18).mark.args[0] == (POSTGRES_VERSION is None or float(POSTGRES_VERSION) >= 18)
