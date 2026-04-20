# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.cli.validate.images_utils import (
    ImageEntry,
    Manifest,
    aggregate,
    classify,
    hatch_contexts,
    parse_env_file,
    scan_compose_file,
    scan_dockerfile,
    scan_python_fixture,
    scan_repo,
    split_ref,
    substitute_env_vars,
)


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


def test_scan_compose_plain(tmp_path):
    compose = tmp_path / 'docker-compose.yaml'
    compose.write_text(
        'services:\n'
        '  redis:\n'
        '    image: redis:7.2\n'
    )
    refs = list(scan_compose_file(compose, contexts=[{}]))
    assert sorted(refs) == ['redis:7.2']


def test_scan_compose_env_var_with_hatch_matrix(tmp_path):
    compose = tmp_path / 'docker-compose.yaml'
    compose.write_text(
        'services:\n'
        '  postgres:\n'
        '    image: "postgres:${POSTGRES_IMAGE}"\n'
    )
    contexts = [{'POSTGRES_IMAGE': '15'}, {'POSTGRES_IMAGE': '16'}]
    refs = list(scan_compose_file(compose, contexts=contexts))
    assert sorted(refs) == ['postgres:15', 'postgres:16']


def test_scan_compose_inline_default(tmp_path):
    compose = tmp_path / 'docker-compose.yaml'
    compose.write_text(
        'services:\n'
        '  pg:\n'
        '    image: "postgres:${POSTGRES_IMAGE:-14}"\n'
    )
    refs = list(scan_compose_file(compose, contexts=[{}]))
    assert refs == ['postgres:14']


def test_scan_compose_unresolved_is_skipped(tmp_path):
    compose = tmp_path / 'docker-compose.yaml'
    compose.write_text(
        'services:\n'
        '  x:\n'
        '    image: "${MYSTERY_IMAGE}"\n'
    )
    refs = list(scan_compose_file(compose, contexts=[{}]))
    assert refs == []


def test_scan_dockerfile_plain(tmp_path):
    df = tmp_path / 'Dockerfile'
    df.write_text('FROM alpine:3.20\n')
    assert list(scan_dockerfile(df, contexts=[{}])) == ['alpine:3.20']


def test_scan_dockerfile_platform_and_as(tmp_path):
    df = tmp_path / 'Dockerfile'
    df.write_text('FROM --platform=linux/amd64 alpine:3.20 AS builder\n')
    assert list(scan_dockerfile(df, contexts=[{}])) == ['alpine:3.20']


def test_scan_dockerfile_arg_default(tmp_path):
    df = tmp_path / 'Dockerfile'
    df.write_text('ARG BASE=alpine:3.20\nFROM ${BASE}\n')
    assert list(scan_dockerfile(df, contexts=[{}])) == ['alpine:3.20']


def test_scan_dockerfile_arg_from_context(tmp_path):
    df = tmp_path / 'Dockerfile'
    df.write_text('ARG BASE\nFROM ${BASE}\n')
    assert list(scan_dockerfile(df, contexts=[{'BASE': 'alpine:3.20'}])) == ['alpine:3.20']


def test_scan_dockerfile_multistage(tmp_path):
    df = tmp_path / 'Dockerfile'
    df.write_text('FROM alpine:3.20 AS build\nFROM debian:12 AS run\n')
    assert sorted(scan_dockerfile(df, contexts=[{}])) == ['alpine:3.20', 'debian:12']


def test_scan_python_docker_run_kwarg(tmp_path):
    src = tmp_path / 'conftest.py'
    src.write_text(
        'from datadog_checks.dev import docker_run\n'
        'def test_x():\n'
        '    with docker_run(compose_file="x", image="mysql:8.0"):\n'
        '        pass\n'
    )
    assert list(scan_python_fixture(src)) == ['mysql:8.0']


def test_scan_python_ignores_dynamic(tmp_path):
    src = tmp_path / 'conftest.py'
    src.write_text(
        'img = "mysql:" + "8.0"\n'
        'def test_x(image):\n'
        '    with docker_run(image=img):\n'
        '        pass\n'
    )
    assert list(scan_python_fixture(src)) == []


def test_scan_python_multiple_calls(tmp_path):
    src = tmp_path / 'conftest.py'
    src.write_text(
        'def a(): return docker_run(image="mysql:8.0")\n'
        'def b(): return docker_run(image="redis:7.2")\n'
    )
    assert sorted(scan_python_fixture(src)) == ['mysql:8.0', 'redis:7.2']


@pytest.mark.parametrize(
    'ref, expected',
    [
        ('redis:7.2', ('redis', '7.2')),
        ('registry.ddbuild.io/dockerhub/redis:7.2', ('registry.ddbuild.io/dockerhub/redis', '7.2')),
        ('alpine', ('alpine', 'latest')),
        ('host:5000/app:1.2.3', ('host:5000/app', '1.2.3')),
    ],
)
def test_split_ref(ref, expected):
    assert split_ref(ref) == expected


def test_classify_mirrored_true():
    prefixes = ['registry.ddbuild.io/dockerhub/']
    assert classify('registry.ddbuild.io/dockerhub/redis', prefixes) is True


def test_classify_mirrored_false():
    prefixes = ['registry.ddbuild.io/dockerhub/']
    assert classify('redis', prefixes) is False


def test_classify_empty_prefix_list():
    assert classify('anything', []) is False


def test_aggregate_groups_by_image_and_sorts():
    refs = [
        ('postgres:15', 'postgres'),
        ('postgres:16', 'postgres'),
        ('postgres:15', 'pgbouncer'),
        ('redis:7.2', 'redis'),
    ]
    manifest = aggregate(refs, mirror_prefixes=['registry.ddbuild.io/dockerhub/'])
    assert manifest == Manifest(
        version=1,
        images=[
            ImageEntry(image='postgres', mirrored=False, tags=['15', '16'], integrations=['pgbouncer', 'postgres']),
            ImageEntry(image='redis', mirrored=False, tags=['7.2'], integrations=['redis']),
        ],
    )


def test_aggregate_marks_mirrored():
    refs = [('registry.ddbuild.io/dockerhub/redis:7.2', 'redis')]
    manifest = aggregate(refs, mirror_prefixes=['registry.ddbuild.io/dockerhub/'])
    assert manifest.images[0].mirrored is True


def test_scan_repo_end_to_end(tmp_path):
    integ = tmp_path / 'postgres'
    (integ / 'tests' / 'compose').mkdir(parents=True)
    (integ / 'tests' / 'compose' / 'docker-compose.yaml').write_text(
        'services:\n'
        '  pg:\n'
        '    image: "postgres:${POSTGRES_IMAGE}"\n'
    )
    (integ / 'hatch.toml').write_text(
        '[[envs.default.matrix]]\n'
        'version = ["15", "16"]\n'
        '[envs.default.overrides]\n'
        'matrix.version.env-vars = "POSTGRES_IMAGE"\n'
    )
    manifest = scan_repo(
        repo_path=tmp_path,
        integrations=['postgres'],
        mirror_prefixes=[],
        exclude_globs=[],
    )
    assert manifest.images == [
        ImageEntry(image='postgres', mirrored=False, tags=['15', '16'], integrations=['postgres']),
    ]
