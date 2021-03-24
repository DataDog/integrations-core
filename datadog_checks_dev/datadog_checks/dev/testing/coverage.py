# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.utils import read_file_binary, write_file_binary


def coverage_sources(check):
    # All paths are relative to each tox.ini
    if check == 'datadog_checks_base':
        package_path = 'datadog_checks/base'
    elif check == 'datadog_checks_dev':
        package_path = 'datadog_checks/dev'
    elif check == 'datadog_checks_downloader':
        package_path = 'datadog_checks/downloader'
    else:
        package_path = f'datadog_checks/{check}'

    return package_path, 'tests'


def fix_coverage_report(check, report_file):
    report = read_file_binary(report_file)

    # Make every check's `tests` directory path unique so they don't get combined in UI
    report = report.replace(b'"tests/', f'"{check}/tests/'.encode('utf-8'))

    write_file_binary(report_file, report)


def pytest_coverage_sources(*checks):
    return ' '.join(' '.join(f'--cov={source}' for source in coverage_sources(check)) for check in checks)