# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from tests.helpers.api import write_file

VALID_METRICS_YAML = """\
jmx_metrics:
  - include:
      domain: my.domain
      bean:
        - my.bean
      attribute:
        Count:
          metric_type: gauge
          alias: my.count
"""

VALID_SPEC_YAML = """\
name: My Check
files:
  - name: conf.yaml.example
    options:
      - template: init_config
        options:
          - template: init_config/jmx
      - template: instances
        options:
          - template: instances/jmx
"""

JMX_CONF_EXAMPLE = """\
init_config:
  is_jmx: true
"""


def _write_jmx_check(repo_path, name, *, metrics=VALID_METRICS_YAML, spec=VALID_SPEC_YAML, conf=JMX_CONF_EXAMPLE):
    write_file(repo_path / name, 'manifest.json', '{}')
    write_file(repo_path / name / 'datadog_checks' / name / 'data', 'metrics.yaml', metrics)
    write_file(repo_path / name / 'datadog_checks' / name / 'data', 'conf.yaml.example', conf)
    write_file(repo_path / name / 'assets' / 'configuration', 'spec.yaml', spec)


@pytest.fixture
def jmx_repo(fake_repo):
    _write_jmx_check(fake_repo.path, 'jmxgood')
    yield fake_repo


def test_validate_jmx_metrics_valid(jmx_repo, ddev):
    result = ddev('validate', 'jmx-metrics', 'jmxgood')
    assert result.exit_code == 0, result.output
    assert 'Validating JMX metrics files for 1 checks' in result.output
    assert '1 valid metrics files' in result.output


@pytest.fixture
def multi_jmx_repo(fake_repo):
    _write_jmx_check(fake_repo.path, 'jmxone')
    _write_jmx_check(fake_repo.path, 'jmxtwo')
    _write_jmx_check(fake_repo.path, 'jmxthree')
    yield fake_repo


@pytest.mark.parametrize('args', [(), ('all',)], ids=['no_arg', 'all'])
def test_validate_jmx_metrics_iterates_all_jmx_integrations(multi_jmx_repo, ddev, args):
    # Regression: empty selection used to trip ddev's `changed`-roots branch, validating zero
    # integrations. Both `ddev validate jmx-metrics` and `ddev validate jmx-metrics all` must
    # iterate every JMX integration in the repo.
    result = ddev('validate', 'jmx-metrics', *args)
    assert result.exit_code == 0, result.output
    assert 'Validating JMX metrics files for 3 checks' in result.output
    assert '3 valid metrics files' in result.output


def test_validate_jmx_metrics_no_jmx_integrations(fake_repo, ddev):
    # dummy and dummy2 in fake_repo do not have is_jmx config
    result = ddev('validate', 'jmx-metrics', 'dummy')
    assert result.exit_code == 0, result.output
    assert 'Validating JMX metrics files for 0 checks' in result.output


def test_validate_jmx_metrics_missing_include(fake_repo, ddev):
    _write_jmx_check(
        fake_repo.path,
        'jmxbad',
        metrics="""\
jmx_metrics:
  - exclude:
      domain: nope
""",
    )
    result = ddev('validate', 'jmx-metrics', 'jmxbad')
    assert result.exit_code == 1, result.output
    assert 'missing include' in result.output
    assert '1 invalid metrics files' in result.output


def test_validate_jmx_metrics_rule_missing_scope(fake_repo, ddev):
    _write_jmx_check(
        fake_repo.path,
        'jmxbad',
        metrics="""\
jmx_metrics:
  - include:
      attribute:
        Count:
          metric_type: gauge
""",
    )
    result = ddev('validate', 'jmx-metrics', 'jmxbad')
    assert result.exit_code == 1, result.output
    assert 'domain, domain_regex or bean attribute is missing' in result.output


def test_validate_jmx_metrics_duplicate_bean_attributes(fake_repo, ddev):
    _write_jmx_check(
        fake_repo.path,
        'jmxbad',
        metrics="""\
jmx_metrics:
  - include:
      domain: d
      bean: my.bean
      attribute:
        Count:
          metric_type: gauge
  - include:
      domain: d
      bean: my.bean
      attribute:
        Count:
          metric_type: counter
""",
    )
    result = ddev('validate', 'jmx-metrics', 'jmxbad')
    assert result.exit_code == 1, result.output
    assert 'bean and attribute combination is a duplicate' in result.output


def test_validate_jmx_metrics_missing_config_spec(fake_repo, ddev):
    # Write a JMX check without the spec.yaml file.
    write_file(fake_repo.path / 'jmxnospec', 'manifest.json', '{}')
    write_file(
        fake_repo.path / 'jmxnospec' / 'datadog_checks' / 'jmxnospec' / 'data', 'metrics.yaml', VALID_METRICS_YAML
    )
    write_file(
        fake_repo.path / 'jmxnospec' / 'datadog_checks' / 'jmxnospec' / 'data', 'conf.yaml.example', JMX_CONF_EXAMPLE
    )
    result = ddev('validate', 'jmx-metrics', 'jmxnospec')
    assert result.exit_code == 1, result.output
    assert 'config spec does not exist' in result.output


def test_validate_jmx_metrics_spec_missing_jmx_templates(fake_repo, ddev):
    _write_jmx_check(
        fake_repo.path,
        'jmxbad',
        spec="""\
name: My Check
files:
  - name: conf.yaml.example
    options:
      - template: init_config
        options: []
      - template: instances
        options: []
""",
    )
    result = ddev('validate', 'jmx-metrics', 'jmxbad')
    assert result.exit_code == 1, result.output
    assert 'does not use `init_config/jmx` template' in result.output
    assert 'does not use `instances/jmx` template' in result.output
