# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import argparse
import collections
import itertools
import json
import os
import pprint
import re
from dataclasses import dataclass
from enum import StrEnum

import requests

stats = collections.Counter()
not_shipped: dict[str, set[str]] = collections.defaultdict(set)

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(HERE, 'templates')
INTEGRATION_DIR = os.path.join(HERE, '..')
DATA_DIR = os.path.join(INTEGRATION_DIR, 'datadog_checks', 'clickhouse', 'data')
TESTS_DIR = os.path.join(INTEGRATION_DIR, 'tests')

PREFIX_ASYNC_METRICS = 'asynchronous_metrics'
PREFIX_PROFILE_EVENTS = 'events'
PREFIX_CURRENT_METRICS = 'metrics'

METRIC_PATTERN = re.compile(r'\s+M\((?P<metric>\w+),\s*"(?P<description>[^"]+)"\)\s*\\?')
METRIC_TYPE_PATTERN = re.compile(r'\s+M\((?P<metric>\w+),\s*"(?P<description>[^"]+)",\s*(?P<type>[\w:]+)\)\s*\\?')
ASYNC_METRICS_PATTERN = re.compile(
    r'new_values\["(?P<metric>[\w.]+)"\]\s*=\s*\{.*,\s*(?P<description>"[^}]*")*?\s*(?:\w+\s*)?\}', re.MULTILINE
)

RAW_SRC_URL = 'https://raw.githubusercontent.com/ClickHouse/ClickHouse/{branch}/src/'
SOURCE_URL_CURRENT_METRICS = RAW_SRC_URL + 'Common/CurrentMetrics.cpp'
SOURCE_URL_PROFILE_EVENTS = RAW_SRC_URL + 'Common/ProfileEvents.cpp'
SOURCE_URL_ASYNC_METRICS = RAW_SRC_URL + 'Common/AsynchronousMetrics.cpp'
SOURCE_URL_SERVER_ASYNC_METRICS = RAW_SRC_URL + 'Interpreters/ServerAsynchronousMetrics.cpp'

INTEGRATION_NAME = 'clickhouse'

# Metrics of this type are submitted twice, as a count and as a total.
TYPE_MONOTONIC_GAUGE = 'monotonic_gauge'


class MetricKind(StrEnum):
    ASYNC_METRICS = 'async_metrics'
    METRICS = 'metrics'
    EVENTS = 'events'


@dataclass
class FileTemplate:
    source_path: str
    target_path: str


@dataclass
class KindSpec:
    """Where the shipped metrics of one system table live."""

    prefix: str
    data_file: str


KIND_SPECS = {
    MetricKind.ASYNC_METRICS: KindSpec(prefix=PREFIX_ASYNC_METRICS, data_file='system_async_metrics.json'),
    MetricKind.EVENTS: KindSpec(prefix=PREFIX_PROFILE_EVENTS, data_file='system_events.json'),
    MetricKind.METRICS: KindSpec(prefix=PREFIX_CURRENT_METRICS, data_file='system_metrics.json'),
}

# The async metrics and profile events tables are not always populated on a freshly started server.
OPTIONAL_KINDS = frozenset({MetricKind.ASYNC_METRICS, MetricKind.EVENTS})

# Metrics that don't come from the system tables above but may show up in a check run, so the tests
# have to tolerate them. The JIT execution counter comes from the legacy query set, which stays
# enabled next to the advanced queries, and only appears once a compiled function is actually run.
EXTRA_OPTIONAL_METRICS = [
    'clickhouse.compilation.function.execute.count',
    'clickhouse.compilation.function.execute.total',
]


TESTS_METRICS_TEMPLATE = FileTemplate(
    source_path='tests_metrics.tpl',
    target_path=os.path.join(TESTS_DIR, 'advanced_metrics.py'),
)


def versions() -> list[str]:
    versions = os.getenv('VERSIONS')
    if not versions:
        print('VERSIONS variable is not defined')
        exit(1)

    return versions.split(',')


def indent_line(string: str, indent: int = 4) -> str:
    return ' ' * indent + string


def read_file(file, encoding='utf-8'):
    with open(file, 'r', encoding=encoding) as f:
        return f.read()


def write_file(file, contents, encoding='utf-8'):
    with open(file, 'w', encoding=encoding) as f:
        f.write(contents)


def generate_queries_file(template: FileTemplate, config: dict):
    source_path = os.path.join(TEMPLATES_DIR, template.source_path)
    if not os.path.exists(source_path):
        print(f'Unknown template file: {source_path}')
        exit(1)

    data = read_file(source_path)
    target_dir = os.path.dirname(template.target_path)
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    write_file(template.target_path, data.format(**config))


def load_shipped_metrics(kind: MetricKind) -> dict[str, str]:
    """Map each metric the integration ships for ``kind`` to its Datadog metric type.

    The ``data/system_*.json`` files are the source of truth for the shipped metric set;
    this script never adds to them. Keys are qualified names such as ``events.Query``, so
    they can be compared directly against what the fetchers read from ClickHouse's source.
    """
    spec_path = os.path.join(DATA_DIR, KIND_SPECS[kind].data_file)
    spec = json.loads(read_file(spec_path))
    prefix = spec['prefix']

    # A group is a list of names, or a name -> scale mapping for scaled types; only names matter here.
    return {f'{prefix}.{name}': metric_type for metric_type, group in spec['items'].items() for name in group}


def fetch_source(url: str, version: str) -> str:
    return requests.get(url.format(branch=version), timeout=10).text


def match_metric_names(source: str, pattern: re.Pattern, prefix: str) -> set[str]:
    return {f'{prefix}.{match.group("metric")}' for match in pattern.finditer(source)}


def fetch_current_metrics(version: str) -> set[str]:
    source = fetch_source(SOURCE_URL_CURRENT_METRICS, version)

    return match_metric_names(source, METRIC_PATTERN, PREFIX_CURRENT_METRICS)


def fetch_profile_events(version: str) -> set[str]:
    source = fetch_source(SOURCE_URL_PROFILE_EVENTS, version)

    # Up to 24.8 profile events are declared without a value type; later versions always carry one.
    # The two forms don't coexist within a version, so matching both keeps this version-agnostic.
    return match_metric_names(source, METRIC_PATTERN, PREFIX_PROFILE_EVENTS) | match_metric_names(
        source, METRIC_TYPE_PATTERN, PREFIX_PROFILE_EVENTS
    )


def fetch_async_metrics(version: str) -> set[str]:
    common = fetch_source(SOURCE_URL_ASYNC_METRICS, version)
    server = fetch_source(SOURCE_URL_SERVER_ASYNC_METRICS, version)

    return match_metric_names(common, ASYNC_METRICS_PATTERN, PREFIX_ASYNC_METRICS) | match_metric_names(
        server, ASYNC_METRICS_PATTERN, PREFIX_ASYNC_METRICS
    )


def fetch_metrics(kind: MetricKind, version: str) -> set[str]:
    match kind:
        case MetricKind.METRICS:
            return fetch_current_metrics(version)
        case MetricKind.EVENTS:
            return fetch_profile_events(version)
        case MetricKind.ASYNC_METRICS:
            return fetch_async_metrics(version)
        case _:
            print(f'Unknown metric kind: {kind}')
            exit(1)


@dataclass
class CalculatedMetrics:
    types: dict[str, str]
    common: set[str]
    unique: dict[str, set[str]]
    optional: bool = False

    def get_metrics_names(self, metrics: set[str]) -> set[str]:
        result = set()
        for name in metrics:
            qualified = f'{INTEGRATION_NAME}.{name}'
            if self.types[name] == TYPE_MONOTONIC_GAUGE:
                result.add(f'{qualified}.count')
                result.add(f'{qualified}.total')
            else:
                result.add(qualified)

        return result

    def get_common_metrics(self) -> list[str]:
        return list(self.get_metrics_names(self.common))

    def get_versioned_metrics(self) -> dict[str, set[str]]:
        result = {}
        for version, metrics in self.unique.items():
            result[version] = self.get_metrics_names(metrics)

        return result


def calculate_metrics(kind: MetricKind) -> CalculatedMetrics:
    shipped = load_shipped_metrics(kind)
    versioned_metrics: dict[str, set[str]] = {}

    # calculate the shipped metrics each version exposes
    for version in versions():
        available = fetch_metrics(kind, version)
        versioned_metrics[version] = available.intersection(shipped)
        not_shipped[kind].update(available.difference(shipped))

    # calculate common metrics among all versions
    common: set[str] = set()
    for prev_version, next_version in itertools.pairwise(versions()):
        prev_metrics: set[str]
        next_metrics: set[str]
        prev_metrics, next_metrics = versioned_metrics[prev_version], versioned_metrics[next_version]
        if common:
            common = common.intersection(prev_metrics).intersection(next_metrics)
        else:
            common = prev_metrics.intersection(next_metrics)

    # calculate unique metrics for each version based on the common list
    diff: dict[str, set[str]] = {}
    for version in versions():
        diff[version] = versioned_metrics[version].difference(common)

    return CalculatedMetrics(types=shipped, common=common, unique=diff, optional=kind in OPTIONAL_KINDS)


def generate_test_data(metrics_data: list[CalculatedMetrics]):
    def printable_array(array: list, indent: int = 4) -> str:
        return pprint.pformat(sorted(array), indent=indent)

    def constant_name(version: str, optional: bool = False) -> str:
        postfix = 'OPTIONAL' if optional else 'METRICS'

        return f'V_{version}_{postfix}'.replace('.', '_')

    def printable_versioned_array(data: dict[str, set[str]], optional: bool = False) -> str:
        result = []
        for version, metrics in data.items():
            const_name = constant_name(version, optional)
            result.append('{const_name} = {items}'.format(const_name=const_name, items=printable_array(metrics)))

        return '\n\n'.join(result)

    def printable_consts_mapper(data: dict[str, set[str]], optional: bool = False, indent: int = 4) -> str:
        result = []
        for version, _ in data.items():
            line = "'{version}': {const}".format(version=version, const=constant_name(version, optional))
            result.append(indent_line(line, indent))

        return ',\n'.join(result)

    def deep_merge(left: dict[str, set[str]], right: dict[str, set[str]]) -> dict[str, set[str]]:
        result = left.copy()
        for key, value in right.items():
            if key in result:
                result[key] = result[key] | value
            else:
                result[key] = value

        return result

    base_metrics: list[str] = []
    optional_metrics: list[str] = list(EXTRA_OPTIONAL_METRICS)
    versioned_base_metrics: dict[str, set[str]] = {}
    versioned_optional_metrics: dict[str, set[str]] = {}

    for data in metrics_data:
        common = data.get_common_metrics()
        versioned = data.get_versioned_metrics()
        if data.optional:
            optional_metrics.extend(common)
            versioned_optional_metrics = deep_merge(versioned_optional_metrics, versioned)
        else:
            base_metrics.extend(common)
            versioned_base_metrics = deep_merge(versioned_base_metrics, versioned)

    config = {
        'versions': ', '.join(versions()),
        'base_metrics': printable_array(base_metrics),
        'optional_metrics': printable_array(optional_metrics),
        'versioned_base_metrics': printable_versioned_array(versioned_base_metrics),
        'versioned_optional_metrics': printable_versioned_array(versioned_optional_metrics, optional=True),
        'base_version_mapper': printable_consts_mapper(versioned_base_metrics),
        'optional_version_mapper': printable_consts_mapper(versioned_optional_metrics, optional=True),
    }
    generate_queries_file(TESTS_METRICS_TEMPLATE, config)


def generate():
    calculated: list[CalculatedMetrics] = []

    for kind in KIND_SPECS:
        metrics = calculate_metrics(kind)
        stats[kind] = len(metrics.types)
        calculated.append(metrics)

    # generate unit test metrics
    generate_test_data(calculated)


def print_stats() -> None:
    print('The number of shipped metrics:')
    for kind, count in stats.items():
        print(f'- {kind}:', count)
    print(f'Total: {stats.total()}')
    print()
    print('Metrics found in the ClickHouse sources that the integration does not ship (left out):')
    for kind, metrics in not_shipped.items():
        print(f'- {kind}:', len(metrics))
    print()
    print('Note: Run `ddev test --fmt clickhouse` to fix formatting and linting errors.')


def main():
    """
    Updates the expected metrics for unit and E2E tests to match the metrics the integration ships.

    The shipped metric set lives in `datadog_checks/clickhouse/data/system_*.json` and is never
    extended by this script: for every version in VERSIONS, the script reads ClickHouse's source
    files, keeps only the metrics that are already shipped, and regenerates the test module from
    `./scripts/templates/tests_metrics.tpl`.

    Test module:
    - contains the base and optional metrics common to every version of ClickHouse in VERSIONS,
      plus the metrics unique to each version

    To fix linters you need to run `ddev test --fmt clickhouse` in the end.
    """
    parser = argparse.ArgumentParser(
        description=main.__doc__,
        epilog='Example: hatch run metrics:generate',
    )
    _ = parser.parse_args()
    generate()
    print_stats()


if __name__ == '__main__':
    main()
