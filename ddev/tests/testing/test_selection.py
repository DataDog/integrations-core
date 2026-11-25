# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import pytest

from ddev.integration.core import Integration
from ddev.repo.core import Repository
from ddev.testing.selection import (
    EnvironmentCatalog,
    e2e_pytest_args,
    load_environment_catalog,
    parse_envs,
    parse_pytest_args,
)
from ddev.utils.fs import Path


@pytest.mark.parametrize(
    'value, expected',
    [(None, None), (' b, a ,b ', ('b', 'a')), ('default', ('default',))],
)
def test_parse_environment_list(value: str | None, expected: tuple[str, ...] | None):
    assert parse_envs(click.Context(click.Command('test')), click.Option(['--envs']), value) == expected


@pytest.mark.parametrize('value', ['', ' ', ',a', 'a,', 'a,,b', 'a, ,b'])
def test_invalid_environment_list(value: str):
    with pytest.raises(click.BadParameter):
        parse_envs(click.Context(click.Command('test')), click.Option(['--envs']), value)


@pytest.mark.parametrize(
    'value, expected',
    [
        ('', ()),
        ('-m "not flaky" "tests/a file.py::test_case"', ('-m', 'not flaky', 'tests/a file.py::test_case')),
        (r'''-k 'a\\b' --override-ini='value="quoted"' '' ''', ('-k', r'a\\b', '--override-ini=value="quoted"', '')),
        ('-k "$(touch sentinel)" ";"', ('-k', '$(touch sentinel)', ';')),
    ],
)
def test_parse_pytest_string(value: str, expected: tuple[str, ...]):
    assert parse_pytest_args(click.Context(click.Command('test')), click.Option(['--pytest-args']), value) == expected


def test_unclosed_pytest_quote():
    with pytest.raises(click.BadParameter, match='No closing quotation'):
        parse_pytest_args(click.Context(click.Command('test')), click.Option(['--pytest-args']), '-m "unit')


@pytest.mark.parametrize(
    'args, expected',
    [
        ((), ('-m', 'e2e')),
        (('-m', 'a or b', '-m', 'not c', '-x'), ('-m', '(a or b) and (not c) and e2e', '-x')),
        (('-ma or b', '-m=not c'), ('-m', '(a or b) and (not c) and e2e')),
        (('--markers', 'tests'), ('-m', 'e2e', '--markers', 'tests')),
        (('--', '-mfile.py'), ('-m', 'e2e', '--', '-mfile.py')),
    ],
)
def test_e2e_marker_intersection(args: tuple[str, ...], expected: tuple[str, ...]):
    assert e2e_pytest_args(args) == expected


def test_e2e_missing_marker_expression():
    with pytest.raises(click.UsageError, match='requires a marker expression'):
        e2e_pytest_args(('-m',))


def test_resolve_matrix_aliases_in_selection_order(catalog: EnvironmentCatalog):
    assert catalog.resolve(('b', 'default', 'a')) == ['b', 'a', 'windows', 'disabled']


def test_unknown_names_are_not_eligibility_exclusions(catalog: EnvironmentCatalog):
    with pytest.raises(click.UsageError, match='Unknown environments: typo'):
        catalog.resolve(('disabled', 'typo'))


@pytest.mark.parametrize(
    'selectors, mode, python_filter, expected',
    [
        (('b', 'a'), 'test_env', '3.13', ['a']),
        (('b',), 'test_env', '3.13', []),
        (('default',), 'e2e_env', None, ['a', 'b']),
        (('a', 'latest'), 'latest_env', None, ['latest']),
        (('a', 'bench'), 'benchmark_env', None, ['bench']),
    ],
)
def test_filters_intersect_resolved_selection(
    catalog: EnvironmentCatalog, selectors: tuple[str, ...], mode: str, python_filter: str | None, expected: list[str]
):
    names = catalog.resolve(selectors)
    selected, excluded = catalog.select(names, mode=mode, platform='linux', python_filter=python_filter)
    assert selected == expected
    assert set(excluded) == set(names) - set(expected)


def test_hatch_catalog_expands_custom_matrix_names(temp_dir: Path):
    integration = temp_dir / 'example'
    integration.mkdir()
    (integration / 'pyproject.toml').write_text('[project]\nname = "example"\nversion = "1.0"\n')
    (integration / 'hatch.toml').write_text(
        '''
[env.collectors.datadog-checks]
[envs.default]
matrix-name-format = "v{value}"
[[envs.default.matrix]]
python = ["3.13"]
product = ["one", "two"]
[envs.default.overrides]
matrix.product.e2e-env = { value = false, if = ["two"] }
'''
    )
    catalog = load_environment_catalog(Integration(integration, temp_dir, Repository('core', str(temp_dir)).config))
    names = catalog.resolve(('default',))
    assert names == ['py3.13-vone', 'py3.13-vtwo']
    selected, excluded = catalog.select(names, mode='e2e_env', platform='linux')
    assert selected == ['py3.13-vone']
    assert excluded == {'py3.13-vtwo': 'e2e-env option'}
