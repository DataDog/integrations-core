# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.ai.runtime.integration_root import resolve_integration_root


@pytest.mark.parametrize(
    "integration,expected_name",
    [
        ("HPE Aruba Edge", "hpe_aruba_edge"),
        ("my-cool.Check", "my_cool_check"),
        ("simple", "simple"),
    ],
)
def test_resolve_integration_root_normalizes_like_ddev_create(tmp_path, integration, expected_name) -> None:
    result = resolve_integration_root(tmp_path, {"integration": integration})
    assert result == tmp_path / expected_name


def test_resolve_integration_root_missing_input_fails_closed(tmp_path) -> None:
    assert resolve_integration_root(tmp_path, {}) is None


@pytest.mark.parametrize("value", ["", "   ", "---", None, 123])
def test_resolve_integration_root_invalid_value_fails_closed(tmp_path, value) -> None:
    assert resolve_integration_root(tmp_path, {"integration": value}) is None


@pytest.mark.parametrize("value", ["ddev/src", "../escape", "/etc", "a/b/c"])
def test_resolve_integration_root_rejects_path_separators(tmp_path, value) -> None:
    """normalize_package_name only touches `-_. `, so a slash would otherwise survive
    normalization and let `integration` name an arbitrary directory outside the
    intended integration root."""
    assert resolve_integration_root(tmp_path, {"integration": value}) is None
