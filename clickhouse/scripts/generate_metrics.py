# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import abc
import argparse
import os
import pprint
import re
import requests


HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(HERE, 'templates')
QUERIES_DIR = os.path.join(HERE, '..', 'datadog_checks', 'clickhouse', 'queries')


class MetricsGenerator(abc.ABC):
    INTEGRATION_PREFIX = 'clickhouse'

    @staticmethod
    def read_file(file, encoding='utf-8'):
        with open(file, 'r', encoding=encoding) as f:
            return f.read()

    @staticmethod
    def write_file(file, contents, encoding='utf-8'):
        with open(file, 'w', encoding=encoding) as f:
            f.write(contents)

    @staticmethod
    def indent(string, _indent=4):
        return ' ' * _indent + string

    @staticmethod
    def format_template(template, config):
        source_path = os.path.join(TEMPLATES_DIR, template)
        target_path = os.path.join(QUERIES_DIR, template)
        file = MetricsGenerator.read_file(source_path)
        MetricsGenerator.write_file(target_path, file.format(**config))

    def integration_metric_name(self, metric):
        return f'{self.INTEGRATION_PREFIX}.{metric}'

    @abc.abstractmethod
    def generate_queries(self):
        return NotImplemented

    @abc.abstractmethod
    def generate_tests(self):
        return NotImplemented


class SystemMetricsGenerator(MetricsGenerator):
    METRIC_PATTERN = re.compile(r'\s+M\((?P<metric>\w+),\s*"(?P<description>[^"]+)"\)\s*\\?')
    METRIC_PREFIX = 'ClickHouseMetrics'
    MODULE_NAME = 'system_metrics.py'

    source_url = 'https://raw.githubusercontent.com/ClickHouse/ClickHouse/{branch}/src/Common/CurrentMetrics.cpp'

    def __init__(self, version: str = None):
        super().__init__()
        self.metrics = {}
        self.version = version or 'master'

    def fetch_metrics(self):
        text = requests.get(self.source_url.format(branch=self.version), timeout=10).text
        metrics = dict(match.groups() for match in self.METRIC_PATTERN.finditer(text))

        return {metric: description for metric, description in metrics.items() if description}

    def prefetch(self):
        if not self.metrics:
            self.metrics = self.fetch_metrics()

        return self.metrics

    def make_template_config(self):
        data = self.prefetch()
        config = {
            'metrics_items': ',\n'.join(self.indent(self.get_metric_header(metric), 16) for metric in data.keys()),
            'metrics_class': 'SystemMetrics',
        }

        return config

    @staticmethod
    def get_metric_header(metric):
        return """
                '{metric}': {{
                    'name': '{metric_name}',
                    'type': 'gauge',
                }}
        """.format(metric=metric, metric_name=SystemMetricsGenerator.metric_name(metric)).strip()

    @staticmethod
    def metric_name(metric):
        return f'{SystemMetricsGenerator.METRIC_PREFIX}_{metric}'

    def generate_queries(self):
        config = self.make_template_config()
        self.format_template(self.MODULE_NAME, config)

    def generate_tests(self):
        data = self.prefetch()
        metrics = []
        for metric in data.keys():
            metrics.append(self.integration_metric_name(self.metric_name(metric)))
        pprint.pprint(metrics, indent=4)


TEMPLATE_GENERATORS = {
    'system_metrics': SystemMetricsGenerator,
}


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Generate metric queries modules from ClickHouse source files. '
            'Module templates for queries are stored in `scripts/templates/` folder.'
        ),
        epilog='Example: hatch run py3.12-25.3:python ./scripts/generate_metrics.py --query system_metrics [--tests]',
    )
    parser.add_argument(
        '--query',
        type=str,
        choices=['system_metrics'],
        required=True,
        help=(
            'Generate according module in the following path `datadog_checks/clickhouse/queries/<query>.py`.'
        ),
    )
    parser.add_argument(
        '-v',
        '--version',
        type=str,
        choices=['24.8', '25.3', '25.5', '25.6', '25.7'],
        help=(
            'Use specific ClickHouse version branch instead of the main one. '
            'See https://github.com/ClickHouse/ClickHouse/blob/master/SECURITY.md for currently supported versions.'
        ),
    )
    parser.add_argument(
        "--tests",
        action="store_true",
        help=(
            'Print the data required for the test specified via `--query` param. '
            'The following module should be updated `tests/metrics.py` afterwards.'
        )
    )
    args = parser.parse_args()
    generate(args.query, args.tests, args.version)


def generate(query: str, print_tests: bool, version: str = None):
    if not os.path.exists(TEMPLATES_DIR):
        print(f'Templates dir {TEMPLATES_DIR} doesn\'t exist.')
        return

    if not os.path.exists(QUERIES_DIR):
        print(f'Queries dir {QUERIES_DIR} doesn\'t exist.')
        return

    if not query in TEMPLATE_GENERATORS:
        print(f'{query} is not supported yet.')
        return

    generator = TEMPLATE_GENERATORS.get(query)(version=version)
    if print_tests:
        generator.generate_tests()
    else:
        generator.generate_queries()


if __name__ == '__main__':
    main()
