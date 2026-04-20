# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations


def test_images_command_registered(fake_repo, ddev):
    result = ddev('validate', 'images', '--help')
    assert result.exit_code == 0, result.output
    assert 'Validate Docker image inventory' in result.output
