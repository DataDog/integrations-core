# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Append manifest-less overrides to ``.ddev/config.toml``.

Per the Building Integrations Without a Manifest spec, new integrations
that omit ``manifest.json`` need three entries under ``[overrides]`` so
the rest of the tooling can still resolve display name, metrics prefix,
and supported platforms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.cli.application import Application

# An override entry maps a directory name to its value: a string (display name,
# metrics prefix) or a list of strings (platforms).
OverrideValue = str | list[str]


def apply_manifestless_overrides(
    app: Application,
    dir_name: str,
    display_name: str,
    metrics_prefix: str,
    platforms: list[str],
) -> None:
    """Add or update the three required overrides in ``.ddev/config.toml``."""
    config_file = app.repo.config
    config_path = config_file.path
    if config_path.is_file():
        data = config_file.load_data()
    else:
        data = {}
        config_path.ensure_parent_dir_exists()

    overrides = data.setdefault('overrides', {})
    _set_entry(overrides, 'display-name', dir_name, display_name)
    _set_entry(overrides, 'metrics-prefix', dir_name, metrics_prefix)

    manifest = overrides.setdefault('manifest', {})
    _set_entry(manifest, 'platforms', dir_name, platforms)

    config_file.save_data(data)


def _set_entry(table: dict[str, dict[str, OverrideValue]], key: str, dir_name: str, value: OverrideValue) -> None:
    section = table.setdefault(key, {})
    section[dir_name] = value
