# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mirror_sync import compute_new_upstream  # noqa: E402


def test_compute_new_upstream_detects_added_image():
    old = {'version': 1, 'images': []}
    new = {
        'version': 1,
        'images': [
            {'image': 'postgres', 'mirrored': False, 'tags': ['15'], 'integrations': ['postgres']},
        ],
    }
    assert compute_new_upstream(old, new) == [('postgres', '15')]


def test_compute_new_upstream_detects_added_tag():
    old = {
        'version': 1,
        'images': [
            {'image': 'postgres', 'mirrored': False, 'tags': ['15'], 'integrations': ['postgres']},
        ],
    }
    new = {
        'version': 1,
        'images': [
            {'image': 'postgres', 'mirrored': False, 'tags': ['15', '16'], 'integrations': ['postgres']},
        ],
    }
    assert compute_new_upstream(old, new) == [('postgres', '16')]


def test_compute_new_upstream_skips_mirrored():
    old = {'version': 1, 'images': []}
    new = {
        'version': 1,
        'images': [
            {
                'image': 'registry.ddbuild.io/dockerhub/redis',
                'mirrored': True,
                'tags': ['7.2'],
                'integrations': ['redis'],
            },
        ],
    }
    assert compute_new_upstream(old, new) == []
