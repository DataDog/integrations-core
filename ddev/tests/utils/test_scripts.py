# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ddev.utils.scripts.ci_matrix
from ddev.utils.scripts.ci_matrix import get_all_targets


def test_non_deprecated_integrations(monkeypatch, repository):
    """
    Test that non-deprecated integrations are included in the CI matrix.
    """
    monkeypatch.setattr(ddev.utils.scripts.ci_matrix, "DEPRECATED_INTEGRATIONS", {})
    assert "tls" in get_all_targets(repository.path)


def test_deprecated_integrations(monkeypatch, repository):
    """
    Test that deprecated integrations are not included in the CI matrix.
    """
    monkeypatch.setattr(ddev.utils.scripts.ci_matrix, "DEPRECATED_INTEGRATIONS", {"tls"})
    assert "tls" not in get_all_targets(repository.path)
