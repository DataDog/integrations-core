# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Behaviour-level tests for the `ddev create` command group."""

from __future__ import annotations

import json

import pytest


@pytest.mark.parametrize(
    'subcommand',
    ['check', 'jmx', 'logs', 'event', 'metrics-crawler'],
)
def test_default_manifestless_writes_overrides_and_skips_manifest(ddev, empty_repo, read_config, subcommand):
    result = ddev(
        'create',
        subcommand,
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux,windows,mac_os',
    )
    assert result.exit_code == 0, result.output

    integration_dir = empty_repo.path / 'my_integration'
    assert integration_dir.is_dir()
    assert not (integration_dir / 'manifest.json').exists()

    data = read_config()
    assert data['overrides']['display-name']['my_integration'] == 'My Integration'
    assert data['overrides']['metrics-prefix']['my_integration'] == 'my_integration.'
    assert data['overrides']['manifest']['platforms']['my_integration'] == ['linux', 'windows', 'mac_os']


def test_include_manifest_writes_manifest_and_skips_overrides(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--include-manifest',
    )
    assert result.exit_code == 0, result.output

    integration_dir = empty_repo.path / 'my_integration'
    assert (integration_dir / 'manifest.json').exists()

    config_toml = empty_repo.path / '.ddev' / 'config.toml'
    assert not config_toml.exists()


def test_skip_manifest_and_include_manifest_conflict(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--skip-manifest',
        '--include-manifest',
    )
    assert result.exit_code != 0
    assert 'mutually exclusive' in result.output


def test_skip_manifest_emits_deprecation_warning(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--skip-manifest',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
    )
    assert result.exit_code == 0, result.output
    assert '--skip-manifest` is deprecated' in result.output


def test_dropped_type_aborts_with_confluence_link(ddev, empty_repo):
    result = ddev('create', 'foo', '--type', 'tile', '--dry-run')
    assert result.exit_code != 0
    assert '6248108729' in result.output


@pytest.mark.parametrize('dropped', ['tile', 'snmp_tile', 'marketplace'])
def test_all_dropped_types_abort(ddev, empty_repo, dropped):
    result = ddev('create', 'foo', '--type', dropped, '--dry-run')
    assert result.exit_code != 0


def test_type_shim_dispatches_to_subcommand(ddev, empty_repo):
    result = ddev(
        'create',
        'my_integration',
        '--type',
        'check',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
        '--dry-run',
    )
    assert result.exit_code == 0, result.output
    assert '--type=check` is deprecated' in result.output
    assert 'Will create' in result.output


def test_dry_run_does_not_write_anything(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
        '--dry-run',
    )
    assert result.exit_code == 0, result.output
    assert not (empty_repo.path / 'my_integration').exists()
    assert not (empty_repo.path / '.ddev' / 'config.toml').exists()


def test_datadog_prefix_rejected(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'datadog_thing',
        '--display-name',
        'Datadog Thing',
        '--metrics-prefix',
        'datadog_thing.',
        '--platforms',
        'linux',
    )
    assert result.exit_code != 0
    assert 'cannot start with' in result.output


@pytest.mark.parametrize('bad_name', ['_my_thing', 'my_thing_', 'foo-', '.bar', 'baz.', 'a@b', 'a/b'])
def test_invalid_integration_name_aborts(ddev, empty_repo, bad_name):
    """Names with leading/trailing non-alphanumerics or disallowed characters abort before any scaffolding.

    Names starting with a dash are blocked earlier by click's option parser; this test covers the
    full surface our own validator owns.
    """
    result = ddev(
        'create',
        'check',
        bad_name,
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
    )
    assert result.exit_code != 0
    assert 'Invalid integration name' in result.output
    assert bad_name in result.output


def test_existing_directory_aborts(ddev, empty_repo):
    (empty_repo.path / 'my_integration').mkdir()
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
    )
    assert result.exit_code != 0
    assert 'already exists' in result.output


def test_overrides_accumulate_across_creates(ddev, empty_repo, read_config):
    for name in ('first_integration', 'second_integration'):
        result = ddev(
            'create',
            'check',
            name,
            '--display-name',
            name.title().replace('_', ' '),
            '--metrics-prefix',
            f'{name}.',
            '--platforms',
            'linux',
        )
        assert result.exit_code == 0, result.output

    data = read_config()
    assert 'first_integration' in data['overrides']['display-name']
    assert 'second_integration' in data['overrides']['display-name']


def test_invalid_platform_rejected(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux,wonkos',
    )
    assert result.exit_code != 0
    assert 'wonkos' in result.output


def test_help_lists_subcommands(ddev):
    result = ddev('create', '--help')
    assert result.exit_code == 0
    for sub in ('check', 'check-only', 'jmx', 'logs', 'event', 'metrics-crawler'):
        assert sub in result.output


def test_all_values_via_flags_never_prompt(ddev, empty_repo, mocker):
    spy = mocker.patch('click.prompt', side_effect=AssertionError('click.prompt should not be called'))
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
    )
    assert result.exit_code == 0, result.output
    spy.assert_not_called()


def test_check_only_requires_existing_manifest(ddev, empty_repo):
    result = ddev(
        'create',
        'check-only',
        'partner_thing',
        '--display-name',
        'Partner Thing',
        '--metrics-prefix',
        'partner_thing.',
        '--platforms',
        'linux',
    )
    assert result.exit_code != 0
    assert 'manifest.json' in result.output


def _write_partner_manifest(integration_dir):
    integration_dir.mkdir()
    (integration_dir / 'manifest.json').write_text(
        json.dumps(
            {
                'author': {
                    'name': 'Partner',
                    'support_email': 'support@partner.com',
                    'homepage': 'https://partner.com',
                    'sales_email': 'sales@partner.com',
                }
            }
        )
    )


def test_check_only_with_prefilled_manifest(ddev, empty_repo):
    _write_partner_manifest(empty_repo.path / 'partner_thing')
    result = ddev(
        'create',
        'check-only',
        'partner_thing',
        '--include-manifest',
    )
    assert result.exit_code == 0, result.output


def test_check_only_writes_into_existing_author_prefixed_directory(ddev, empty_repo):
    """`check_only` scaffolded files land in the directory that holds the existing manifest."""
    integration_dir = empty_repo.path / 'partner_thing'
    _write_partner_manifest(integration_dir)

    result = ddev(
        'create',
        'check-only',
        'partner_thing',
        '--include-manifest',
    )
    assert result.exit_code == 0, result.output

    # Files must land in the manifest's directory, not a sibling stripped-name directory.
    assert (integration_dir / 'pyproject.toml').is_file()
    assert (integration_dir / 'datadog_checks' / 'partner_thing' / '__about__.py').is_file()
    assert not (empty_repo.path / 'thing').exists()


def test_check_only_manifestless_writes_overrides_for_integration_dir(ddev, empty_repo, read_config):
    """Manifest-less check-only writes overrides keyed by the on-disk integration directory."""
    integration_dir = empty_repo.path / 'partner_thing'
    _write_partner_manifest(integration_dir)

    result = ddev(
        'create',
        'check-only',
        'partner_thing',
        '--display-name',
        'Partner Thing',
        '--metrics-prefix',
        'partner_thing.',
        '--platforms',
        'linux,windows,mac_os',
    )
    assert result.exit_code == 0, result.output

    # Files must land in the existing partner_thing directory, not a sibling stripped-name directory.
    assert (integration_dir / 'pyproject.toml').is_file()
    assert not (empty_repo.path / 'thing').exists()

    data = read_config()
    assert data['overrides']['display-name']['partner_thing'] == 'Partner Thing'
    assert data['overrides']['metrics-prefix']['partner_thing'] == 'partner_thing.'
    assert data['overrides']['manifest']['platforms']['partner_thing'] == ['linux', 'windows', 'mac_os']


def test_bare_positional_aborts_with_subcommand_hint(ddev, empty_repo):
    """A bare-positional `ddev create NAME` points the user at the new subcommand surface."""
    result = ddev('create', 'ACME')
    assert result.exit_code != 0
    # The error must mention at least one of the new subcommands so users have something to copy.
    output = result.output.lower()
    assert 'ddev create check' in output or 'ddev create logs' in output
    assert 'acme' in output.lower()


def test_global_no_interactive_flag_aborts_when_required_flags_missing(ddev, empty_repo):
    """The root-group `--no-interactive` flag aborts `create` when required flags are missing."""
    result = ddev('--no-interactive', 'create', 'check', 'my_integration')
    assert result.exit_code != 0
    assert '--display-name' in result.output
    assert '--metrics-prefix' in result.output
    assert '--platforms' in result.output


def test_type_flag_without_value_aborts_with_targeted_message(ddev, empty_repo):
    """`ddev create NAME --type` (no value) must name the missing value, not the generic 'use a subcommand' message."""
    result = ddev('create', 'my_integration', '--type')
    assert result.exit_code != 0
    assert '--type' in result.output
    assert 'requires a value' in result.output


def test_global_quiet_suppresses_tree_and_keeps_headline(ddev, empty_repo):
    """`ddev -q create ...` suppresses the file-tree printout but still emits the one-line `Created` headline."""
    result = ddev(
        '-q',
        'create',
        'check',
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
    )
    assert result.exit_code == 0, result.output
    assert 'my_integration' in result.output
    # The full tree must NOT appear in quiet mode.
    assert '└──' not in result.output and '├──' not in result.output


def test_dry_run_tree_uses_pipe_middle_for_non_last_directory(ddev, empty_repo):
    """Non-last directories at depth >= 2 in the dry-run tree use `├──`, not `└──`."""
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
        '--include-manifest',
        '--dry-run',
    )
    assert result.exit_code == 0, result.output
    # The `assets/` subtree has both `configuration/` and `dashboards/`; the non-last
    # of the two must use the middle connector. Prior bug always rendered `└──`.
    assert '├── configuration' in result.output or '├── dashboards' in result.output


def test_jmx_template_defaults_take_no_arguments(ddev, empty_repo, tmp_path):
    """The scaffolded JMX `defaults.py` defines zero-argument functions.

    `instance.py` invokes them as `getattr(defaults, ...)()` with no arguments; a `(field, value)`
    signature would crash every JMX-scaffolded integration at runtime with `TypeError`.
    """
    import importlib.util
    import inspect

    result = ddev(
        'create',
        'jmx',
        'smoke_jmx',
        '--display-name',
        'Smoke JMX',
        '--metrics-prefix',
        'smoke_jmx.',
        '--platforms',
        'linux,windows,mac_os',
        '--include-manifest',
    )
    assert result.exit_code == 0, result.output

    defaults_path = empty_repo.path / 'smoke_jmx' / 'datadog_checks' / 'smoke_jmx' / 'config_models' / 'defaults.py'
    assert defaults_path.is_file(), defaults_path

    spec = importlib.util.spec_from_file_location('smoke_jmx_defaults', str(defaults_path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    public_callables = [
        getattr(module, name) for name in dir(module) if not name.startswith('_') and callable(getattr(module, name))
    ]
    assert public_callables, 'defaults.py exposed no callables'
    for fn in public_callables:
        sig = inspect.signature(fn)
        assert len(sig.parameters) == 0, f'{fn.__name__}{sig} should take no arguments'
        fn()  # raises TypeError if it doesn't


def test_type_flag_consumes_flag_shaped_value_as_missing(ddev, empty_repo):
    """A flag-shaped token following `--type` is treated as a missing value, not parsed as the type."""
    result = ddev('create', 'my_integration', '--type', '--dry-run')
    assert result.exit_code != 0
    # The targeted "requires a value" message must fire, not the generic "Unknown integration type".
    assert 'requires a value' in result.output
    assert 'Unknown integration type' not in result.output


def test_check_only_non_object_manifest_aborts(ddev, empty_repo):
    """A `manifest.json` whose top-level JSON is not an object aborts with a clear message."""
    integration_dir = empty_repo.path / 'partner_thing'
    integration_dir.mkdir()
    (integration_dir / 'manifest.json').write_text('["not", "an", "object"]')

    result = ddev(
        'create',
        'check-only',
        'partner_thing',
        '--include-manifest',
    )
    assert result.exit_code != 0
    assert 'does not contain a JSON object' in result.output


@pytest.mark.parametrize(
    'json_author_name',
    [
        '""',  # empty
        '"   "',  # whitespace-only
        '"!@#$"',  # all-symbol -> normalize_display_name collapses to ""
        '"   !!!  "',  # whitespace + all-symbol
    ],
)
def test_check_only_rejects_unusable_author_name(ddev, empty_repo, json_author_name):
    """Author names that normalize to an empty value abort before any path computation."""
    integration_dir = empty_repo.path / 'partner_thing'
    integration_dir.mkdir()
    (integration_dir / 'manifest.json').write_text(f'{{"author": {{"name": {json_author_name}}}}}')

    result = ddev(
        'create',
        'check-only',
        'partner_thing',
        '--include-manifest',
    )
    assert result.exit_code != 0
    assert 'Unable to determine author from manifest' in result.output
    # No scaffolded files must have escaped to the filesystem root or anywhere outside the integration.
    assert not (integration_dir / 'pyproject.toml').exists()


def test_check_only_partial_write_failure_does_not_recommend_deleting_directory(ddev, empty_repo, fail_on_second_write):
    """`check_only` partial-write errors list scaffolded files instead of recommending directory deletion."""
    integration_dir = empty_repo.path / 'partner_thing'
    integration_dir.mkdir()
    (integration_dir / 'manifest.json').write_text(
        json.dumps({'author': {'name': 'Partner', 'support_email': 'p@p.com'}})
    )

    result = ddev(
        'create',
        'check-only',
        'partner_thing',
        '--include-manifest',
    )
    assert result.exit_code != 0
    # The message must NOT tell the user to remove the directory (it holds their manifest).
    assert 'Remove `' not in result.output or str(integration_dir) not in result.output
    # The message MUST point at the scaffolded files specifically.
    assert 'scaffolded files' in result.output or 'No files were written' in result.output


def test_non_check_only_partial_write_failure_recommends_deleting_directory(ddev, empty_repo, fail_on_second_write):
    """For `check` (and other types where the dir was freshly created), the message stays directory-scoped."""
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
        '--include-manifest',
    )
    assert result.exit_code != 0
    assert 'Remove `' in result.output
    assert 'my_integration' in result.output
