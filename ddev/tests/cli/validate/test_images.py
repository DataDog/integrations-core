# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.cli.validate.images_utils import substitute_env_vars


def test_images_command_registered(fake_repo, ddev):
    result = ddev('validate', 'images', '--help')
    assert result.exit_code == 0, result.output
    assert 'Validate Docker image inventory' in result.output


@pytest.mark.parametrize(
    'template, context, expected',
    [
        ('postgres:15', {}, 'postgres:15'),
        ('postgres:${TAG}', {'TAG': '15'}, 'postgres:15'),
        ('postgres:$TAG', {'TAG': '15'}, 'postgres:15'),
        ('postgres:${TAG:-14}', {}, 'postgres:14'),
        ('postgres:${TAG:-14}', {'TAG': '16'}, 'postgres:16'),
        ('postgres:${TAG-14}', {'TAG': ''}, 'postgres:'),
        ('postgres:${TAG:-14}', {'TAG': ''}, 'postgres:14'),
        ('literal $$sign', {}, 'literal $sign'),
        ('${IMAGE}:${TAG}', {'IMAGE': 'redis', 'TAG': '7.2'}, 'redis:7.2'),
    ],
)
def test_substitute_env_vars_resolves(template, context, expected):
    assert substitute_env_vars(template, context) == expected


def test_substitute_env_vars_returns_none_when_unresolved():
    assert substitute_env_vars('postgres:${MISSING}', {}) is None
    assert substitute_env_vars('$MISSING', {}) is None
