# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

from datadog_checks.dev.tooling.constants import set_root
from datadog_checks.dev.tooling.manifest_utils import get_metric_prefix


def write_manifest(root, check, prefix):
    check_dir = os.path.join(root, check)
    os.makedirs(check_dir, exist_ok=True)
    manifest = {
        "manifest_version": "2.0.0",
        "assets": {"integration": {"metrics": {"prefix": prefix}}},
    }
    with open(os.path.join(check_dir, 'manifest.json'), 'w') as f:
        json.dump(manifest, f)


def write_overrides(root, overrides):
    ddev_dir = os.path.join(root, '.ddev')
    os.makedirs(ddev_dir, exist_ok=True)
    lines = ['[overrides.metrics-prefix]']
    lines.extend(f'{check} = "{prefix}"' for check, prefix in overrides.items())
    with open(os.path.join(ddev_dir, 'config.toml'), 'w') as f:
        f.write('\n'.join(lines) + '\n')


def test_prefers_manifest_prefix(tmp_path, restore_root):
    set_root(str(tmp_path))
    write_manifest(tmp_path, 'zk', 'zookeeper.')
    write_overrides(tmp_path, {'zk': 'ignored.'})

    assert get_metric_prefix('zk') == 'zookeeper.'


def test_falls_back_to_config_toml_override(tmp_path, restore_root):
    set_root(str(tmp_path))
    os.makedirs(os.path.join(tmp_path, 'krakend'), exist_ok=True)
    write_overrides(tmp_path, {'krakend': 'krakend.api.'})

    assert get_metric_prefix('krakend') == 'krakend.api.'


def test_returns_empty_string_when_undeclared(tmp_path, restore_root):
    set_root(str(tmp_path))
    os.makedirs(os.path.join(tmp_path, 'unknown_check'), exist_ok=True)

    assert get_metric_prefix('unknown_check') == ''
