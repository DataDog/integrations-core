# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import csv
from collections import defaultdict
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


def read_metadata_rows(metadata_file):
    """
    Iterate over the rows of a `metadata.csv` file.
    """
    with metadata_file.open(encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=',')

        # Read header
        reader._fieldnames = reader.fieldnames

        for line_no, row in enumerate(reader, 2):
            yield line_no, row


def normalize_metric_name(metric_name):
    """Copy pasted from the backend normalization code.
    Extracted from dogweb/datalayer/metrics/query/metadata.py:normalize_metric_name
    Metrics in metadata.csv need to be formatted this way otherwise, syncing metadata will fail.
    Function not exported as a util, as this is different than AgentCheck.normalize. This function just makes sure
    that whatever is in the metadata.csv is understandable by the backend.
    """
    from ddev.cli.validate import metadata_utils

    metric_name = metadata_utils.METRIC_REPLACEMENT.sub("_", metric_name)
    return metadata_utils.METRIC_DOTUNDERSCORE_CLEANUP.sub(".", metric_name).strip("_")


def check_duplicate_values(current_check, line, row, header_name, duplicates, fail=None):
    """Check if the given column value has been seen before.
    Output a warning and return True if so.
    """
    if row[header_name] and row[header_name] not in duplicates:
        duplicates.add(row[header_name])
    elif row[header_name] != '':
        message = f"{current_check.name}:{line} `{row[header_name]}` is a duplicate {header_name}\n"
        if fail:
            return (True, message)
        else:
            return (False, message)
    return (False, '')


@click.command(short_help='Validate `metadata.csv` files')
@click.argument('integrations', nargs=-1)
@click.option(
    '--check-duplicates', is_flag=True, help='Output warnings if there are duplicate short names and descriptions'
)
@click.option('--show-warnings', '-w', is_flag=True, help='Show warnings in addition to failures')
@click.pass_obj
def metadata(app: Application, integrations: tuple[str, ...], check_duplicates: bool, show_warnings: bool):
    """
    Validate `metadata.csv` files

    If `check` is specified, only the check will be validated, if check value is
    'changed' will only apply to changed checks, an 'all' or empty `check` value
    will validate all README files.
    """
    from ddev.cli.validate import metadata_utils

    validation_tracker = app.create_validation_tracker('Metrics validation')

    excluded = set(app.repo.config.get('/overrides/validate/metrics/exclude', []))
    for current_check in app.repo.integrations.iter(integrations):
        if current_check.name in excluded or not current_check.has_metrics:
            continue

        errors = False
        error_message = ""
        warning_message = ""

        if current_check.name.startswith('datadog_checks_'):
            continue

        metric_prefix = current_check.manifest.get("/assets/integration/metrics/prefix", "")
        metadata_file = current_check.metrics_file

        # To make logging less verbose, common errors are counted for current check
        metric_prefix_count: defaultdict[str, int] = defaultdict(int)
        empty_count: defaultdict[str, int] = defaultdict(int)
        empty_warning_count: defaultdict[str, int] = defaultdict(int)
        duplicate_name_set: set = set()
        duplicate_short_name_set: set = set()
        duplicate_description_set: set = set()

        metric_prefix_error_shown = False
        if metadata_file.stat().st_size == 0:
            errors = True

            error_message += (
                f"{current_check.name} metadata file is empty. This file needs the header row at the minimum.\n"
            )

        for line, row in read_metadata_rows(metadata_file):
            # determine if number of columns is complete by checking for None values
            # DictReader populates missing columns with None https://docs.python.org/3.8/library/csv.html#csv.DictReader
            if None in row.values():
                errors = True

                error_message += f"{current_check.name}:{line} {row['metric_name']} has the wrong number of columns.\n"
                continue

            # all headers exist, no invalid headers
            all_keys = set(row)
            if all_keys != metadata_utils.ALL_HEADERS:
                invalid_headers = all_keys.difference(metadata_utils.ALL_HEADERS)
                if invalid_headers:
                    errors = True

                    error_message += f"{current_check.name}:{line} Invalid column {invalid_headers}.\n"

                missing_headers = metadata_utils.ALL_HEADERS.difference(all_keys)
                if missing_headers:
                    errors = True

                    error_message += f"{current_check.name}:{line} Missing columns {missing_headers}.\n"
                continue

            # check duplicate metric name
            duplicate_metric_name = check_duplicate_values(
                current_check, line, row, 'metric_name', duplicate_name_set, fail=True
            )
            if duplicate_metric_name[0]:
                errors = True

                error_message += duplicate_metric_name[1]

            if check_duplicates:
                warning_message += check_duplicate_values(
                    current_check, line, row, 'short_name', duplicate_short_name_set
                )[1]
                warning_message += check_duplicate_values(
                    current_check, line, row, 'description', duplicate_description_set
                )[1]

            normalized_metric_name = normalize_metric_name(row['metric_name'])
            if row['metric_name'] != normalized_metric_name:
                errors = True

                error_message += f"{current_check.name}:{line} Metric name '{row['metric_name']}' is not valid, "
                error_message += f"it should be normalized as {normalized_metric_name}.\n"

            # metric_name header
            if metric_prefix:
                prefix = row['metric_name'].split('.')[0]
                if not row['metric_name'].startswith(metadata_utils.ALLOWED_PREFIXES) and not row[
                    'metric_name'
                ].startswith(metric_prefix):
                    metric_prefix_count[prefix] += 1
            else:
                errors = True
                if not metric_prefix_error_shown and current_check.name not in metadata_utils.PROVIDER_INTEGRATIONS:
                    metric_prefix_error_shown = True

                    error_message += f'{current_check.name}:{line} metric_prefix does not exist in manifest.\n'

            # metric_type header
            if row['metric_type'] and row['metric_type'] not in metadata_utils.VALID_METRIC_TYPE:
                errors = True

                error_message += f"{current_check.name}:{line} `{row['metric_type']}` is an invalid metric_type.\n"

            # unit_name header
            if row['unit_name'] and row['unit_name'] not in metadata_utils.VALID_UNIT_NAMES:
                errors = True

                error_message += f"{current_check.name}:{line} `{row['unit_name']}` is an invalid unit_name.\n"

            # per_unit_name header
            if row['per_unit_name'] and row['per_unit_name'] not in metadata_utils.VALID_UNIT_NAMES:
                errors = True
                error_message += f"{current_check.name}:{line} `{row['per_unit_name']}` is an invalid per_unit_name.\n"

            # Check if unit/per_unit is valid
            if (
                row['unit_name'] in metadata_utils.VALID_TIME_UNIT_NAMES
                and row['per_unit_name'] in metadata_utils.VALID_TIME_UNIT_NAMES
            ):
                errors = True
                error_message += (
                    f"{current_check.name}:{line} `{row['unit_name']}/{row['per_unit_name']}` unit is invalid, "
                )
                error_message += "use the fraction unit instead.\n"

            # integration header
            integration = row['integration']
            normalized_integration = current_check.normalized_display_name
            if integration != normalized_integration and normalized_integration not in excluded:
                errors = True

                error_message += f"{current_check.name}:{line} integration: `{row['integration']}` should be: "
                error_message += f"{normalized_integration}.\n"

            # orientation header
            if row['orientation'] and row['orientation'] not in metadata_utils.VALID_ORIENTATION:
                errors = True

                error_message += f"{current_check.name}:{line} `{row['orientation']}` is an invalid orientation.\n"

            # empty required fields
            for header in metadata_utils.REQUIRED_HEADERS:
                if not row[header]:
                    empty_count[header] += 1

            # empty description field, description is recommended
            if not row['description']:
                empty_warning_count['description'] += 1

            elif "|" in row['description']:
                errors = True

                error_message += f"{current_check.name}:{line} `{row['metric_name']}` description contains a `|`.\n"

            # check if there is unicode
            elif any(not content.isascii() for content in row.values()):
                errors = True

                error_message += (
                    f"{current_check.name}:{line} `{row['metric_name']}` description contains unicode characters.\n"
                )

            # exceeds max allowed length of description
            elif len(row['description']) > metadata_utils.MAX_DESCRIPTION_LENGTH:
                errors = True

                error_message += (
                    f"{current_check.name}:{line} `{row['metric_name']}` description exceeds the max length: "
                )
                error_message += f"{metadata_utils.MAX_DESCRIPTION_LENGTH} for descriptions.\n"
            if row['interval'] and not row['interval'].isdigit():
                errors = True

                error_message += f"{current_check.name}:{line} interval should be an int, found '{row['interval']}'.\n"

            if row['curated_metric']:
                metric_types = row['curated_metric'].split('|')
                if len(set(metric_types)) != len(metric_types):
                    errors = True

                    error_message += f"{current_check.name}:{line} `{row['metric_name']}` contains "
                    error_message += "duplicate curated_metric types.\n"

                for curated_metric_type in metric_types:
                    if curated_metric_type not in metadata_utils.VALID_CURATED_METRIC_TYPES:
                        errors = True

                        error_message += f"{current_check.name}:{line} `{row['metric_name']}` contains invalid "
                        error_message += f"curated metric type: {curated_metric_type}\n"

        for header, count in empty_count.items():
            errors = True

            error_message += f'{integration}: {header} is empty in {count} rows.\n'

        for prefix, count in metric_prefix_count.items():
            errors = True

            error_message += (
                f"{current_check.name}: `{prefix}` appears {count} time(s) and does not match metric_prefix "
            )
            error_message += "defined in the manifest.\n"

        error_message = error_message[:-1]
        if errors:
            validation_tracker.error(
                (current_check.display_name, str(metadata_file.relative_to(app.repo.path))),
                message=error_message,
            )
        else:
            validation_tracker.success()

        if show_warnings or warning_message:
            for header, count in empty_warning_count.items():
                warning_message += f'{current_check.name}: {header} is empty in {count} rows.'

            validation_tracker.warning(
                (current_check.display_name, str(metadata_file.relative_to(app.repo.path))),
                message=warning_message,
            )

    validation_tracker.display()

    if validation_tracker.errors:
        app.abort()
