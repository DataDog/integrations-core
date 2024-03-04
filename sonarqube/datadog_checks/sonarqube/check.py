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
    _DEFAULT_COMPONENTS_DISCOVERY_LIMIT = 10

    def __init__(self, name, init_config, instances):
        super(SonarqubeCheck, self).__init__(name, init_config, instances)

        self._web_endpoint = self.instance.get('web_endpoint', '')
        self._tags = ['endpoint:{}'.format(self._web_endpoint)]
        self._tags.extend(self.instance.get('tags', []))

        # Construct the component data on the first check run
        self._components = None
        self._components_discovery = None
        self.check_initializations.append(self.parse_config)

    def check(self, _):
        try:
            self.collect_metadata()
            self.collect_metrics()
        except RequestException as e:
            self.log.error('RequestException: %s', e)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, tags=self._tags, message=str(e))
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)

    @AgentCheck.metadata_entrypoint
    def collect_metadata(self):
        self.collect_version()

    def collect_metrics(self):
        available_metrics = self.discover_available_metrics()
        self.log.debug('available_metrics: %s', available_metrics)
        self.collect_components(available_metrics)
        self.collect_components_discovery(available_metrics)

    def collect_components(self, available_metrics):
        for component, (tag_name, should_collect_metric) in self._components.items():
            self.log.debug('processing component %s', component)
            self.collect_metrics_from_component(available_metrics, component, tag_name, should_collect_metric)

    def collect_components_discovery(self, available_metrics):
        if not self._components_discovery:
            self.log.debug('components_discovery is None')
            return
        self.log.debug('components_discovery: %s', self._components_discovery)
        available_components = self.discover_available_components()
        self.log.debug('available_components: %s', available_components)
        (discovery_limit, components_discovery) = self._components_discovery
        collected_components = 0
        for pattern, (should_collect_component, tag_name, should_collect_metric) in components_discovery.items():
            self.log.debug('processing pattern `%s`', pattern)
            for component in available_components:
                if component in self._components:
                    self.log.debug(
                        'component `%s` included in `components`, it will not be processed by `components_discovery`',
                        component,
                    )
                    continue
                self.log.debug('processing component `%s`', component)
                if should_collect_component(component):
                    self.collect_metrics_from_component(available_metrics, component, tag_name, should_collect_metric)
                    collected_components += 1
                    self.log.debug(
                        'collected %d component%s', collected_components, '' if collected_components == 1 else 's'
                    )
                    if collected_components == discovery_limit:
                        return
                else:
                    self.log.debug(
                        'component `%s` should not be collected '
                        '(see `exclude` list in `components_discovery` key config)',
                        component,
                    )

    def collect_metrics_from_component(self, available_metrics, component, tag_name, should_collect_metric):
        self.log.debug('collecting metrics from component `%s`', component)
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
        self.log.debug('/api/measures/component response: %s', response.json())
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
            self.log.debug('/api/metrics/search response: %s', response.json())
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
                    self.log.debug('Unknown metric category: %s', domain)
                    continue
                available_metrics[key] = '{}.{}'.format(category, key)
            page += 1
        return available_metrics

    def discover_available_components(self):
        available_components = []
        page = 1
        seen = 0
        total = -1
        while seen != total:
            response = self.http.get(
                '{}/api/components/search'.format(self._web_endpoint), params={'qualifiers': 'TRK', 'p': page}
            )
            response.raise_for_status()
            self.log.debug('/api/components/search response: %s', response.json())
            search_results = response.json()
            total = search_results['paging']['total']
            for component in search_results['components']:
                seen += 1
                available_components.append(component['key'])
            page += 1
        return available_components

    def collect_version(self):
        response = self.http.get('{}/api/server/version'.format(self._web_endpoint))
        response.raise_for_status()
        self.log.debug('/api/server/version response: %s', response.text)
        version = response.text
        if not version:
            self.log.warning('The SonarQube version was not found in response')
            return
        # The version comes in like `8.5.0.37579` though sometimes there is no build part
        version_parts = dict(zip(('major', 'minor', 'patch', 'build'), version.split('.')))
        self.log.debug('version: %s', version_parts)
        self.set_metadata('version', version, scheme='parts', final_scheme='semver', part_map=version_parts)

    def parse_config(self):
        self._parse_defaults()
        self._parse_components()
        self._parse_components_discovery()

    def _parse_defaults(self):
        self._default_tag = self.instance.get('default_tag', 'component')
        if not isinstance(self._default_tag, str):
            raise ConfigurationError('The `default_tag` setting must be a string')
        self._default_include = self.compile_metric_patterns(self.instance, 'default_include')
        self._default_exclude = self.compile_metric_patterns(self.instance, 'default_exclude')

    def _parse_components(self):
        components = self.instance.get('components', {})
        self.log.debug('components: %s', components)
        if not isinstance(components, dict):
            raise ConfigurationError('The `components` setting must be a mapping')
        components_data = {}
        for component, config in components.items():
            if config is None:
                config = {}
            if not isinstance(config, dict):
                raise ConfigurationError('Component `{}` must refer to a mapping'.format(component))
            include_metric = self.create_matcher(
                self.compile_metric_patterns(config, 'include') or self._default_include,
                default=True,
            )
            exclude_metric = self.create_matcher(
                self.compile_metric_patterns(config, 'exclude') or self._default_exclude,
                default=False,
            )
            tag_name = config.get('tag', self._default_tag)
            if not isinstance(tag_name, str):
                raise ConfigurationError('The `tag` setting must be a string')
            components_data[component] = (
                tag_name,
                lambda _metric, _include_metric=include_metric, _exclude_metric=exclude_metric: _include_metric(_metric)
                and not _exclude_metric(_metric),
            )
        self._components = components_data

    def _parse_components_discovery(self):
        components_discovery = self.instance.get('components_discovery', None)
        self.log.debug('components_discovery: %s', components_discovery)
        if not components_discovery:
            return
        components_discovery_data = {}
        exclude_component = self.create_matcher(
            self.compile_component_patterns(components_discovery, 'exclude'),
            default=False,
        )
        for pattern, config in components_discovery.get('include', {}).items():
            self.log.debug('pattern: %s, config: %s', pattern, config)
            if config is None:
                config = {}
            if not isinstance(config, dict):
                raise ConfigurationError('Pattern `{}` must refer to a mapping'.format(pattern))
            include_component = self.create_matcher(re.compile(pattern), default=True)
            include_metric = self.create_matcher(
                self.compile_metric_patterns(config, 'include') or self._default_include,
                default=True,
            )
            exclude_metric = self.create_matcher(
                self.compile_metric_patterns(config, 'exclude') or self._default_exclude,
                default=False,
            )
            tag_name = config.get('tag', self._default_tag)
            if not isinstance(tag_name, str):
                raise ConfigurationError('The `tag` setting must be a string')
            components_discovery_data[pattern] = (
                lambda _component, _include=include_component, _exclude=exclude_component: _include(_component)
                and not _exclude(_component),
                tag_name,
                lambda _metric, _include_metric=include_metric, _exclude_metric=exclude_metric: _include_metric(_metric)
                and not _exclude_metric(_metric),
            )
        self._components_discovery = (
            components_discovery.get('limit', self._DEFAULT_COMPONENTS_DISCOVERY_LIMIT),
            components_discovery_data,
        )

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
    def compile_component_patterns(config, field):
        component_patterns = config.get(field, [])
        if not isinstance(component_patterns, list):
            raise ConfigurationError('The `{}` setting must be an array'.format(field))
        patterns = []
        for i, component_pattern in enumerate(component_patterns, 1):
            if not isinstance(component_pattern, str):
                raise ConfigurationError('Pattern #{} in `{}` setting must be a string'.format(i, field))
            # Ensure dots are treated as literal
            component_pattern = component_pattern.replace('\\.', '.').replace('.', '\\.')
            # Get rid of any explicit start modifiers
            component_pattern = component_pattern.lstrip('^')
            # Match from the start by default
            component_pattern = '^{}'.format(component_pattern)
            patterns.append(component_pattern)
        return re.compile('|'.join(patterns)) if patterns else None

    @staticmethod
    def create_matcher(pattern, default):
        if pattern is None:

            def matcher(value):
                return default

        else:

            def matcher(value):
                return not not pattern.search(value)

        return matcher

    @staticmethod
    def is_valid_metric(metric):
        return (
            not metric['hidden']
            and metric['type'] in NUMERIC_TYPES
            # https://github.com/DataDog/integrations-core/pull/8552
            and not metric['key'].startswith('new_')
        )
