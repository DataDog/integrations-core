# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import argparse
import csv
import itertools
import os
import pprint
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

import requests

# should be in sync with env versions from hatch.toml
VERSIONS = ['24.8', '25.3', '25.5', '25.6', '25.7']

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(HERE, 'templates')
INTEGRATION_DIR = os.path.join(HERE, '..')
QUERIES_DIR = os.path.join(INTEGRATION_DIR, 'datadog_checks', 'clickhouse', 'queries')
TESTS_DIR = os.path.join(INTEGRATION_DIR, 'tests')
METADATAFILE_PATH = os.path.join(INTEGRATION_DIR, 'metadata.csv')

GENERATED_FILE_TEMPLATES = {
    'metrics.py': os.path.join(TESTS_DIR, 'metrics.py'),
    'system_events.py': os.path.join(QUERIES_DIR, 'system_events.py'),
    'system_metrics.py': os.path.join(QUERIES_DIR, 'system_metrics.py'),
}

PREFIX_CURRENT_METRICS = 'ClickHouseMetrics'
PREFIX_PROFILE_EVENTS = 'ClickHouseProfileEvents'


METRIC_PATTERN = re.compile(r'\s+M\((?P<metric>\w+),\s*"(?P<description>[^"]+)"\)\s*\\?')
METRIC_TYPE_PATTERN = re.compile(r'\s+M\((?P<metric>\w+),\s*"(?P<description>[^"]+)",\s*(?P<type>[\w:]+)\)\s*\\?')

RAW_SRC_URL = 'https://raw.githubusercontent.com/ClickHouse/ClickHouse/{branch}/src/Common/'
SOURCE_URL_CURRENT_METRICS = RAW_SRC_URL + 'CurrentMetrics.cpp'
SOURCE_URL_PROFILE_EVENTS = RAW_SRC_URL + 'ProfileEvents.cpp'

INTEGRATION_NAME = 'clickhouse'

VALUE_TYPE_COUNTER = 'counter'
VALUE_TYPE_NUMBER = 'ValueType::Number'
VALUE_TYPE_BYTES = 'ValueType::Bytes'
VALUE_TYPE_MILLISECONDS = 'ValueType::Milliseconds'
VALUE_TYPE_MICROSECONDS = 'ValueType::Microseconds'
VALUE_TYPE_NANOSECONDS = 'ValueType::Nanoseconds'

# each value represents the following tuple (<metric-type>, <scale>)
DD_VALUE_TYPES = {
    VALUE_TYPE_COUNTER: ('gauge', None),
    VALUE_TYPE_NUMBER: ('monotonic_gauge', None),
    VALUE_TYPE_BYTES: ('monotonic_gauge', None),
    VALUE_TYPE_MILLISECONDS: ('temporal_percent', 'millisecond'),
    VALUE_TYPE_MICROSECONDS: ('temporal_percent', 'microsecond'),
    VALUE_TYPE_NANOSECONDS: ('temporal_percent', 'nanosecond'),
}
VALUE_TYPE_POSTFIX_24_8 = {
    'Milliseconds': VALUE_TYPE_MILLISECONDS,
    'Microseconds': VALUE_TYPE_MICROSECONDS,
    'Nanoseconds': VALUE_TYPE_NANOSECONDS,
}


def indent_line(string: str, indent: int=4) -> str:
    return ' ' * indent + string

def read_file(file, encoding='utf-8'):
    with open(file, 'r', encoding=encoding) as f:
        return f.read()

def write_file(file, contents, encoding='utf-8'):
    with open(file, 'w', encoding=encoding) as f:
        f.write(contents)

def generate_queries_file(template: str, config: dict):
    target_path = GENERATED_FILE_TEMPLATES.get(template)
    if target_path is None:
        print(f'Unknown template file: {template}')
        exit(1)
    template_path = os.path.join(TEMPLATES_DIR, template)
    data = read_file(template_path)
    write_file(target_path, data.format(**config))


@dataclass
class ClickhouseMetric:
    name: str
    description: str
    prefix: str
    value_type: str | None = None

    def __eq__(self, other: 'ClickhouseMetric'):
        return self.name == other.name

    def __lt__(self, other: 'ClickhouseMetric'):
        return self.name < other.name

    def metric_name(self) -> str:
        return f'{self.prefix}_{self.name}'

    def integration_name(self, postfix: str = '') -> str:
        return f'{INTEGRATION_NAME}.{self.metric_name()}{postfix}'

    def unit_name(self) -> str:
        return self.scale() or ''

    def metric_type_info(self) -> tuple[str, str | None]:
        if self.value_type is None:
            return ('gauge', None)

        return DD_VALUE_TYPES[self.value_type]

    def type(self) -> str:
        return self.metric_type_info()[0]

    def scale(self) -> str | None:
        return self.metric_type_info()[1]

    def get_query_item(self) -> str:
        metric_type, scale = self.metric_type_info()

        metric_scale = ''
        if scale is not None:
            metric_scale = ", 'scale': '{scale}'".format(scale=scale)

        return "'{metric}': {{'name': '{metric_name}', 'type': '{metric_type}'{metric_scale}}}".format(
            metric=self.name,
            metric_name=self.metric_name(),
            metric_type=metric_type,
            metric_scale=metric_scale,
        )


def fetch_current_metrics(version: str) -> dict[str, ClickhouseMetric]:
    raw_metrics = requests.get(SOURCE_URL_CURRENT_METRICS.format(branch=version), timeout=10).text

    result = {}
    for match in METRIC_PATTERN.finditer(raw_metrics):
        name, description = match.groups()
        m = ClickhouseMetric(name=name, description=description, prefix=PREFIX_CURRENT_METRICS)
        result[m.metric_name()] = m

    return result


def fetch_profile_events(version: str) -> dict[str, ClickhouseMetric]:
    raw_metrics = requests.get(SOURCE_URL_PROFILE_EVENTS.format(branch=version), timeout=10).text

    result = {}
    if version == '24.8':
        for match in METRIC_PATTERN.finditer(raw_metrics):
            name, description = match.groups()
            m = ClickhouseMetric(
                name=name,
                description=description,
                prefix=PREFIX_PROFILE_EVENTS,
                value_type=extract_value_type_24_8(name),
            )
            result[m.metric_name()] = m
    else:
        for match in METRIC_TYPE_PATTERN.finditer(raw_metrics):
            name, description, value_type = match.groups()
            m = ClickhouseMetric(
                name=name,
                description=description,
                prefix=PREFIX_PROFILE_EVENTS,
                value_type=value_type,
            )
            result[m.metric_name()] = m

    return result


def extract_value_type_24_8(metric: str):
    for metric_postfix in VALUE_TYPE_POSTFIX_24_8:
        if metric.endswith(metric_postfix):
            return VALUE_TYPE_POSTFIX_24_8[metric_postfix]

    return VALUE_TYPE_COUNTER


def generate_queries(template: str, metrics: Iterable[ClickhouseMetric]):
    config = {
        'items': ',\n'.join(indent_line(metric.get_query_item(), 16) for metric in sorted(metrics)),
    }
    generate_queries_file(template, config)


def generate_metadata_file(metrics: Iterable[ClickhouseMetric]):
    HEADERS = [
        'metric_name',
        'metric_type',
        'interval',
        'unit_name',
        'per_unit_name',
        'description',
        'orientation',
        'integration',
        'short_name',
        'curated_metric',
        'sample_tags',
    ]
    metadata = []

    def add_metadata(metric: ClickhouseMetric, metric_type: str, metric_postfix: str = ''):
        meta = dict.fromkeys(HEADERS, '')
        meta['metric_name'] = metric.integration_name(postfix=metric_postfix)
        meta['metric_type'] = metric_type
        meta['description'] = metric.description
        meta['orientation'] = 0
        meta['integration'] = INTEGRATION_NAME
        meta['unit_name'] = metric.unit_name()
        metadata.append(meta)

    for metric in metrics:
        match metric.type():
            case 'monotonic_gauge':
                add_metadata(metric, metric_postfix='.count', metric_type='count')
                add_metadata(metric, metric_postfix='.total', metric_type='gauge')
            case _:
                add_metadata(metric, metric_type='gauge')

    with open(METADATAFILE_PATH, 'w', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(sorted(metadata, key=lambda x: x.get('metric_name')))


@dataclass
class CalculatedMetrics:
    all: dict[str, ClickhouseMetric]
    common: set[str]
    unique: dict[str, set[str]]
    optional: bool = False

    def get_metrics_names(self, metrics: set[str]) -> set[str]:
        result = set()
        for name in metrics:
            metric = self.all[name]
            match metric.type():
                case 'monotonic_gauge':
                    result.add(metric.integration_name(postfix='.count'))
                    result.add(metric.integration_name(postfix='.total'))
                case _:
                    result.add(metric.integration_name())

        return result

    def get_common_metrics(self) -> list[str]:
        return list(self.get_metrics_names(self.common))


    def get_versioned_metrics(self) -> dict[str, set[str]]:
        result = {}
        for version, metrics in self.unique.items():
            result[version] = self.get_metrics_names(metrics)

        return result


class MetricKind(StrEnum):
    METRICS = 'metrics'
    EVENTS = 'events'


def calculate_metrics(metric_kind: str) -> CalculatedMetrics:
    all_metrics: dict[str, ClickhouseMetric] = {}
    versioned_metrics: dict[str, set[str]] = {}
    is_optional = False

    # calculate metrics for each version and the overall list
    for version in VERSIONS:
        match metric_kind:
            case MetricKind.METRICS:
                metrics = fetch_current_metrics(version)
            case MetricKind.EVENTS:
                metrics = fetch_profile_events(version)
                is_optional = True
            case _:
                print(f'Unknown metric kind: {metric_kind}')
                exit(1)
        all_metrics.update(metrics)
        versioned_metrics[version] = set(metrics.keys())

    # calculate common metrics among all versions
    common: set[str] = set()
    for prev_version, next_version in itertools.pairwise(VERSIONS):
        prev_metrics: set[str]
        next_metrics: set[str]
        prev_metrics, next_metrics = versioned_metrics[prev_version], versioned_metrics[next_version]
        if common:
            common = common.intersection(prev_metrics).intersection(next_metrics)
        else:
            common = prev_metrics.intersection(next_metrics)

    # calculate unique metrics for each version based on the common list
    diff: dict[str, set[str]] = {}
    for version in VERSIONS:
        diff[version] = versioned_metrics[version].difference(common)

    return CalculatedMetrics(all=all_metrics, common=common, unique=diff, optional=is_optional)


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

    base_metrics: list[str] = []
    optional_metrics: list[str] = []
    versioned_base_metrics: dict[str, set[str]] = {}
    versioned_optional_metrics: dict[str, set[str]] = {}

    for data in metrics_data:
        common = data.get_common_metrics()
        versioned = data.get_versioned_metrics()
        if data.optional:
            optional_metrics.extend(common)
            versioned_optional_metrics.update(versioned)
        else:
            base_metrics.extend(common)
            versioned_base_metrics.update(versioned)

    config = {
        'versions': ', '.join(VERSIONS),
        'base_metrics': printable_array(base_metrics),
        'optional_metrics': printable_array(optional_metrics),
        'versioned_base_metrics': printable_versioned_array(versioned_base_metrics),
        'versioned_optional_metrics': printable_versioned_array(versioned_optional_metrics, optional=True),
        'base_version_mapper': printable_consts_mapper(versioned_base_metrics),
        'optional_version_mapper': printable_consts_mapper(versioned_optional_metrics, optional=True),
    }
    generate_queries_file('metrics.py', config)


def generate():
    all: dict[str, ClickhouseMetric] = {}
    all_metrics = calculate_metrics(MetricKind.METRICS)
    all_events = calculate_metrics(MetricKind.EVENTS)
    all.update(all_metrics.all)
    all.update(all_events.all)

    generate_queries('system_metrics.py', all_metrics.all.values())
    generate_queries('system_events.py', all_events.all.values())

    generate_metadata_file(all.values())

    generate_test_data([all_metrics, all_events])


def main():
    """
    Generates and updates query modules for agent's Check, metrics for unit tests and metadata.csv file.
    Templates are stored in `./scripts/templates/` folder.

    Query modules:
    - generated from ClickHouse source files (except AsynchronousMetrics for now)
    - contain a complete intersection of all available metrics (for each supported system table)

    Test module:
    - contains all the base and optional metrics for each version of ClickHouse for unit tests

    Metadata.csv file:
    - contains all the metrics supported by ClickHouse integration

    After generating the files, you need to re-run all linters.
    """
    parser = argparse.ArgumentParser(
        description=main.__doc__,
        epilog='Example: hatch run py3.12-25.3:python ./scripts/generate_metrics.py',
    )
    _ = parser.parse_args()
    generate()

if __name__ == '__main__':
    main()
