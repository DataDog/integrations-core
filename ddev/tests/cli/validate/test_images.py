# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.cli.validate.images_utils import hatch_contexts, parse_env_file, substitute_env_vars


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


def test_parse_env_file(tmp_path):
    env = tmp_path / '.env'
    env.write_text(
        '# comment\n'
        'POSTGRES_IMAGE=15\n'
        '\n'
        'REDIS_IMAGE="7.2"\n'
        "KAFKA_VERSION='7.5.0'\n"
        'EMPTY=\n'
    )
    assert parse_env_file(env) == {
        'POSTGRES_IMAGE': '15',
        'REDIS_IMAGE': '7.2',
        'KAFKA_VERSION': '7.5.0',
        'EMPTY': '',
    }


def test_parse_env_file_missing_returns_empty(tmp_path):
    assert parse_env_file(tmp_path / 'absent.env') == {}


def test_hatch_contexts_static_env_vars(tmp_path):
    (tmp_path / 'hatch.toml').write_text(
        '[envs.default.env-vars]\n'
        'POSTGRES_IMAGE = "15"\n'
    )
    contexts = hatch_contexts(tmp_path / 'hatch.toml')
    assert contexts == [{'POSTGRES_IMAGE': '15'}]


def test_hatch_contexts_matrix_expansion(tmp_path):
    (tmp_path / 'hatch.toml').write_text(
        '[[envs.default.matrix]]\n'
        'version = ["15", "16", "17"]\n'
        '[envs.default.overrides]\n'
        'matrix.version.env-vars = "POSTGRES_IMAGE"\n'
    )
    contexts = hatch_contexts(tmp_path / 'hatch.toml')
    assert sorted(ctx['POSTGRES_IMAGE'] for ctx in contexts) == ['15', '16', '17']


def test_hatch_contexts_missing_file(tmp_path):
    assert hatch_contexts(tmp_path / 'absent.toml') == [{}]
