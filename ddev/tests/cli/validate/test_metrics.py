# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from pathlib import Path

import pytest

from .conftest import _fake_repo as _base_fake_repo
from .conftest import write_file


def _fake_repo(tmp_path_factory, config_file, name):
    repo = _base_fake_repo(tmp_path_factory, config_file, name)

    write_file(
        repo.path / 'metadata_integration',
        'manifest.json',
        """{
          "manifest_version": "2.0.0",
          "app_uuid": "15b15f01-b342-4001-89ac-9e92fc4f3234",
          "app_id": "druid",
          "display_on_public_website": true,
          "assets": {
            "integration": {
              "metrics": {
                "prefix": "metadata_integration.",
                "check": [],
                "metadata_path": "metadata.csv"
              }
            }
          }
        }
""",
    )

    write_file(
        repo.path / 'metadata_integration',
        'metadata.csv',
        """metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric
metadata_integration.metric_b,gauge,,,,My metric B,0,metadata_integration,,
metadata_integration.metric_a,gauge,,,,My metric A,0,metadata_integration,,
""",
    )

    return repo


@pytest.fixture
def fake_repo(
    tmp_path_factory,
    config_file,
):
    yield _fake_repo(tmp_path_factory, config_file, 'core')


@pytest.fixture
def fake_extras_repo(tmp_path_factory, config_file):
    yield _fake_repo(tmp_path_factory, config_file, 'extras')


@pytest.fixture
def fake_marketplace_repo(tmp_path_factory, config_file):
    yield _fake_repo(tmp_path_factory, config_file, 'marketplace')


def test_metrics_empty(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    Path(metrics_file).write_text('')

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache metadata file is empty. This file needs the header row at the
                minimum.

        Errors: 1
        """
    )


def test_column_number(ddev, repository, helpers):
    outfile = os.path.join('apache', 'metadata.csv')

    write_file(
        repository.path / 'apache',
        'metadata.csv',
        helpers.dedent(
            """
        metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric
        apache.conns_total,gauge,,connection,,The number of connections.,0,apache,
        """
        ),
    )

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:2 apache.conns_total has the wrong number of columns.

        Errors: 1
        """
    )


def test_header_missing_invalid(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[0] = metrics[0][:-1] + "_badheader\n"

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics[:7])

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:2 Invalid column {{'curated_metric_badheader'}}.
                apache:2 Missing columns {{'curated_metric'}}.
                apache:3 Invalid column {{'curated_metric_badheader'}}.
                apache:3 Missing columns {{'curated_metric'}}.
                apache:4 Invalid column {{'curated_metric_badheader'}}.
                apache:4 Missing columns {{'curated_metric'}}.
                apache:5 Invalid column {{'curated_metric_badheader'}}.
                apache:5 Missing columns {{'curated_metric'}}.
                apache:6 Invalid column {{'curated_metric_badheader'}}.
                apache:6 Missing columns {{'curated_metric'}}.
                apache:7 Invalid column {{'curated_metric_badheader'}}.
                apache:7 Missing columns {{'curated_metric'}}.

        Errors: 1
        """
    )


def test_normalized_metrics(ddev, repository, helpers):
    outfile = os.path.join('apache', 'metadata.csv')

    write_file(
        repository.path / 'apache',
        'metadata.csv',
        helpers.dedent(
            """
        metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric
        apache.conns-total,gauge,,connection,,The number of connections.,0,apache,,
        """
        ),
    )

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:2 Metric name 'apache.conns-total' is not valid, it should be
                normalized as apache.conns_total.

        Errors: 1
        """
    )


def test_manifest_metric_prefix_dne(ddev, repository, helpers):
    check = 'apache'
    manifest_file = repository.path / check / 'manifest.json'
    outfile = os.path.join('apache', 'metadata.csv')

    manifest = json.loads(manifest_file.read_text())
    del manifest['assets']['integration']['metrics']['prefix']
    manifest_file.write_text(json.dumps(manifest))

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output

    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:2 metric_prefix does not exist in manifest.

        Errors: 1
        """
    )


def test_invalid_metric_type(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[1] = metrics[1].replace('gauge', 'invalid_metric_type')

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:2 `invalid_metric_type` is an invalid metric_type.

        Errors: 1
        """
    )


def test_invalid_unit_name(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[1] = metrics[1].replace('connection', 'invalid_unit_name')

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:2 `invalid_unit_name` is an invalid unit_name.

        Errors: 1
        """
    )


def test_invalid_per_unit_name(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[6] = metrics[6].replace('second', 'invalid_per_unit_name')

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:7 `invalid_per_unit_name` is an invalid per_unit_name.

        Errors: 1
        """
    )


def test_invalid_unit_fraction(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[6] = metrics[6].replace(',,byte,', ',,day,')

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:7 `day/second` unit is invalid, use the fraction unit instead.

        Errors: 1
        """
    )


def test_integration_header(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[6] = metrics[6].replace(',apache,', ',apache___,')

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:7 integration: `apache___` should be: apache.

        Errors: 1
        """
    )


def test_invalid_orientation(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[6] = metrics[6].replace(',0,', ',2,')

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:7 `2` is an invalid orientation.

        Errors: 1
        """
    )


def test_invalid_vbar(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[6] = metrics[6].replace('The number', 'The | number')

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:7 `apache.net.bytes_per_s` description contains a `|`.

        Errors: 1
        """
    )


def test_invalid_unicode(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[6] = metrics[6].replace('The number', 'The ± number')

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:7 `apache.net.bytes_per_s` description contains unicode
                characters.

        Errors: 1
        """
    )


def test_max_length(ddev, repository, helpers):
    long_string = "Lorem ipsum dolor sit amet consectetur adipiscing elit finibus vulputate commodo"
    max_length = long_string * 5

    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[6] = metrics[6].replace('The number', max_length)

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:7 `apache.net.bytes_per_s` description exceeds the max length:
                400 for descriptions.

        Errors: 1
        """
    )


def test_interval_integer(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[6] = metrics[6].replace('gauge,,', 'gauge,not_a_digit,')

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:7 interval should be an int, found 'not_a_digit'.

        Errors: 1
        """
    )


def test_duplicate_curated_metric(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[6] = metrics[6][:-1] + "cpu|cpu\n"

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:7 `apache.net.bytes_per_s` contains duplicate curated_metric
                types.

        Errors: 1
        """
    )


def test_invalid_curated_metric(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[6] = metrics[6][:-1] + "invalid_curated_metric\n"

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:7 `apache.net.bytes_per_s` contains invalid curated metric type:
                invalid_curated_metric

        Errors: 1
        """
    )


def test_header_empty(ddev, repository, helpers):
    metrics_file = repository.path / 'apache' / 'metadata.csv'
    outfile = os.path.join('apache', 'metadata.csv')

    with metrics_file.open(encoding='utf-8') as file:
        metrics = file.readlines()

    metrics[6] = metrics[6].replace('gauge', '')

    with metrics_file.open(mode='w', encoding='utf-8') as file:
        file.writelines(metrics)

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache: metric_type is empty in 1 rows.

        Errors: 1
        """
    )


def test_prefix_match(ddev, repository, helpers):
    outfile = os.path.join('apache', 'metadata.csv')

    write_file(
        repository.path / 'apache',
        'metadata.csv',
        helpers.dedent(
            """
        metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric
        invalid_metric_prefix.conns,gauge,,connection,,The number of connections.,0,apache,,
        """
        ),
    )

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache: `invalid_metric_prefix` appears 1 time(s) and does not match
                metric_prefix defined in the manifest.

        Errors: 1
        """
    )


def test_duplicate_metric_name(ddev, repository, helpers):
    outfile = os.path.join('apache', 'metadata.csv')

    write_file(
        repository.path / 'apache',
        'metadata.csv',
        helpers.dedent(
            """
        metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric
        apache.conns_async_keep_alive,gauge,,connection,,The number of asynchronous closing connections.,0,apache,,
        apache.conns_async_keep_alive,gauge,,connection,,description,0,apache,,
        """
        ),
    )

    result = ddev("validate", "metadata", 'apache')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:3 `apache.conns_async_keep_alive` is a duplicate metric_name

        Errors: 1
        """
    )


def test_warnings(ddev, repository, helpers):
    outfile = os.path.join('apache', 'metadata.csv')

    write_file(
        repository.path / 'apache',
        'metadata.csv',
        helpers.dedent(
            """
        metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric
        apache.conns_async_closing,gauge,,connection,,T,0,apache,ConnsAsyncKeepAlive,
        apache.conns_async_keep_alive,gauge,,connection,,,0,apache,ConnsAsyncKeepAlive,
        """
        ),
    )

    result = ddev("validate", "metadata", 'apache', '--check-duplicates', '--show-warnings')

    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── Apache
            └── {outfile}

                apache:3 `ConnsAsyncKeepAlive` is a duplicate short_name
                apache: description is empty in 1 rows.

        Passed: 1
        Warnings: 1
        """
    )


def test_metrics_passing(ddev, helpers):
    result = ddev('validate', 'metadata', 'postgres')

    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Metrics validation

        Passed: 1
        """
    )


def test_metrics_ordered(fake_repo, ddev, helpers):
    write_file(
        fake_repo.path / "metadata_integration",
        'metadata.csv',
        """metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric
metadata_integration.metric_a,gauge,,,,My metric A,0,metadata_integration,,
metadata_integration.metric_b,gauge,,,,My metric B,0,metadata_integration,,
""",
    )

    result = ddev('validate', 'metadata', 'metadata_integration')

    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Metrics validation

        Passed: 1
        """
    )


def test_metrics_not_ordered(fake_repo, ddev, helpers):
    outfile = os.path.join('metadata_integration', 'metadata.csv')
    result = ddev('validate', 'metadata', 'metadata_integration')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Metrics validation
        └── metadata_integration
            └── {outfile}

                metadata_integration: metadata.csv is not sorted by metric name.
                Run `ddev validate metadata metadata_integration --sync` to sort it.

        Errors: 1
        """
    )


def test_metrics_not_ordered_sync(fake_repo, ddev, helpers):
    result = ddev('validate', 'metadata', 'metadata_integration', '--sync')

    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Metrics validation

        Passed: 1
        """
    )

    result = ddev('validate', 'metadata', 'metadata_integration')

    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Metrics validation

        Passed: 1
        """
    )


def test_metrics_not_ordered_but_allowed(fake_repo, ddev, helpers):
    write_file(
        fake_repo.path / ".ddev",
        'config.toml',
        """[overrides.validate.metrics]
unsorted = [
    'metadata_integration',
]
""",
    )

    result = ddev('validate', 'metadata', 'metadata_integration')

    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Metrics validation

        Passed: 1
        """
    )


@pytest.mark.parametrize('repo_fixture', ['fake_extras_repo', 'fake_marketplace_repo'])
def test_metrics_not_ordered_but_not_in_core(repo_fixture, ddev, helpers, request):
    request.getfixturevalue(repo_fixture)
    result = ddev('validate', 'metadata', 'metadata_integration')

    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Metrics validation

        Passed: 1
        """
    )
