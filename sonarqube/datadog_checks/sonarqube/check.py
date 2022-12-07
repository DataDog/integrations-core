# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from requests.exceptions import RequestException

from datadog_checks.base import AgentCheck, ConfigurationError

from .constants import CATEGORIES, NUMERIC_TYPES


class SonarqubeCheck(AgentCheck):
    __NAMESPACE__ = 'sonarqube'
    SERVICE_CHECK_CONNECT = 'api_access'

    def __init__(self, name, init_config, instances):
        super(SonarqubeCheck, self).__init__(name, init_config, instances)

        self._web_endpoint = self.instance.get('web_endpoint', '')
        self._tags = ['endpoint:{}'.format(self._web_endpoint)]
        self._tags.extend(self.instance.get('tags', []))

        # Construct the component data on the first check run
        self._components = None

        self.check_initializations.append(self.parse_config)

    def check(self, _):
        try:
            self.collect_metadata()
            self.collect_metrics()
        except RequestException as e:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, tags=self._tags, message=str(e))
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)

    @AgentCheck.metadata_entrypoint
    def collect_metadata(self):
        self.collect_version()

    def collect_metrics(self):
        available_metrics = self.discover_available_metrics()

        for component, (tag_name, should_collect_metric) in self._components.items():
            keys_to_query = []

            for key, metric in available_metrics.items():
                if should_collect_metric(metric):
                    keys_to_query.append(key)

            if not keys_to_query:
                self.log.warning('Pattern for component `%s` does not match any available metrics', component)

            response = self.http.get(
                '{}/api/measures/component'.format(self._web_endpoint),
                params={'component': component, 'metricKeys': ','.join(keys_to_query)},
            )
            response.raise_for_status()
            metric_data = response.json()

            for measure in metric_data['component']['measures']:
                tags = ['{}:{}'.format(tag_name, component)]
                tags.extend(self._tags)

                self.gauge(available_metrics[measure['metric']], measure['value'], tags=tags)

    def discover_available_metrics(self):
        available_metrics = {}

        page = 1
        seen = 0
        total = -1

        while seen != total:
            response = self.http.get('{}/api/metrics/search'.format(self._web_endpoint), params={'p': page})
            response.raise_for_status()

            search_results = response.json()
            total = search_results['total']

            for metric in search_results['metrics']:
                seen += 1

                if not self.is_valid_metric(metric):
                    continue

                domain = metric['domain']
                key = metric['key']

                category = CATEGORIES.get(domain)
                if category is None:
                    self.log.warning('Unknown metric category: %s', domain)
                    continue

                available_metrics[key] = '{}.{}'.format(category, key)

            page += 1

        return available_metrics

    def collect_version(self):
        response = self.http.get('{}/api/server/version'.format(self._web_endpoint))
        response.raise_for_status()
        version = response.text
        if not version:
            self.log.warning('The SonarQube version was not found in response')
            return

        # The version comes in like `8.5.0.37579` though sometimes there is no build part
        version_parts = {name: part for name, part in zip(('major', 'minor', 'patch', 'build'), version.split('.'))}

        self.set_metadata('version', version, scheme='parts', final_scheme='semver', part_map=version_parts)

    def parse_config(self):
        components = self.instance.get('components', {})
        if not isinstance(components, dict):
            raise ConfigurationError('The `components` setting must be a mapping')
        elif not components:
            raise ConfigurationError('The `components` setting must be defined')

        default_component_tag = self.instance.get('default_tag', 'component')
        if not isinstance(default_component_tag, str):
            raise ConfigurationError('The `default_tag` setting must be a string')

        default_metric_inclusion_pattern = self.compile_metric_patterns(self.instance, 'default_include')
        default_metric_exclusion_pattern = self.compile_metric_patterns(self.instance, 'default_exclude')

        component_data = {}
        for component, config in components.items():
            if config is None:
                config = {}

            if not isinstance(config, dict):
                raise ConfigurationError('Component `{}` must refer to a mapping'.format(component))

            include_metric = self.create_metric_matcher(
                self.compile_metric_patterns(config, 'include') or default_metric_inclusion_pattern,
                default=True,
            )
            exclude_metric = self.create_metric_matcher(
                self.compile_metric_patterns(config, 'exclude') or default_metric_exclusion_pattern,
                default=False,
            )

            tag_name = config.get('tag', default_component_tag)
            if not isinstance(tag_name, str):
                raise ConfigurationError('The `tag` setting must be a string')

            component_data[component] = (
                tag_name,
                lambda metric, include_metric=include_metric, exclude_metric=exclude_metric: include_metric(metric)
                and not exclude_metric(metric),
            )

        self._components = component_data

    @staticmethod
    def compile_metric_patterns(config, field):
        metric_patterns = config.get(field, [])
        if not isinstance(metric_patterns, list):
            raise ConfigurationError('The `{}` setting must be an array'.format(field))

        patterns = []
        for i, metric_pattern in enumerate(metric_patterns, 1):
            if not isinstance(metric_pattern, str):
                raise ConfigurationError('Pattern #{} in `{}` setting must be a string'.format(i, field))

            # Ensure dots are treated as literal
            metric_pattern = metric_pattern.replace('\\.', '.').replace('.', '\\.')

            # Get rid of any explicit start modifiers
            metric_pattern = metric_pattern.lstrip('^')

            # We only search on `<CATEGORY>.<KEY>`
            metric_pattern = re.sub(r'^sonarqube(\\.)?', '', metric_pattern)
            if not metric_pattern:
                raise ConfigurationError('Pattern #{} in `{}` setting must be more specific'.format(i, field))

            # Match from the start by default
            metric_pattern = '^{}'.format(metric_pattern)

            patterns.append(metric_pattern)

        return re.compile('|'.join(patterns)) if patterns else None

    @staticmethod
    def create_metric_matcher(pattern, default):
        if pattern is None:

            def metric_matcher(metric):
                return default

        else:

            def metric_matcher(metric):
                return not not pattern.search(metric)

        return metric_matcher

    @staticmethod
    def is_valid_metric(metric):
        return (
            not metric['hidden']
            and metric['type'] in NUMERIC_TYPES
            # https://github.com/DataDog/integrations-core/pull/8552
            and not metric['key'].startswith('new_')
        )
