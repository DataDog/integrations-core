# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from requests.exceptions import RequestException

from datadog_checks.base import AgentCheck, ConfigurationError

from .discovery_filter import DiscoveryFilter
from .sonarqube_api import SonarqubeAPI


class SonarqubeCheck(AgentCheck):
    __NAMESPACE__ = 'sonarqube'
    SERVICE_CHECK_CONNECT = 'api_access'

    def __init__(self, name, init_config, instances):
        super(SonarqubeCheck, self).__init__(name, init_config, instances)
        self._validate_config()
        self._projects_discovery_matcher = DiscoveryFilter('projects', self.log, self._projects)
        self._api = SonarqubeAPI(self.log, self.http, self._web_endpoint)

    def _validate_config(self):
        self._validate_web_endpoint()
        self._validate_tags()
        self._validate_projects()
        if self._projects is None:
            self._validate_default_tag()
            self._validate_default_include()
            self._validate_default_exclude()
            self._validate_components()

    def _validate_web_endpoint(self):
        self._web_endpoint = self.instance.get('web_endpoint')
        if self._web_endpoint is None:
            raise ConfigurationError('\'web_endpoint\' setting must be defined')
        if not isinstance(self._web_endpoint, str):
            raise ConfigurationError('\'web_endpoint\' setting must be a string')

    def _validate_tags(self):
        tags = self.instance.get('tags', [])
        if not isinstance(tags, list):
            raise ConfigurationError('\'tags\' setting must be a list')
        self._tags = ['endpoint:{}'.format(self._web_endpoint)] + tags

    def _validate_projects(self):
        self._projects = None
        self.log.debug('validating \'projects\': %s', self.instance)
        projects = self.instance.get('projects', None)
        if projects is not None and isinstance(projects, dict):
            self.log.debug('\'projects\' found in config: %s', projects)
            self._projects = {'keys': [], 'discovery': projects.get('discovery', {})}
            self._default_tag = projects.get('default_tag', 'component')
            self.log.debug('default_tag: %s', self._default_tag)
            self._default_metrics_limit = projects.get('default_metrics_limit', 100)
            self.log.debug('default_metrics_limit: %s', self._default_metrics_limit)
            self._default_metrics_include = projects.get('default_metrics_include', ['^.*'])
            self.log.debug('default_metrics_include: %s', self._default_metrics_include)
            self._default_metrics_exclude = projects.get('default_metrics_exclude', ['^.*\\.new_.*'])
            self.log.debug('default_metrics_exclude: %s', self._default_metrics_exclude)
            keys = projects.get('keys', [])
            self.log.debug('keys: %s', keys)
            for keys_item in keys:
                if isinstance(keys_item, dict):
                    self._projects['keys'].append({list(keys_item.keys())[0]: list(keys_item.values())[0]})
                elif isinstance(keys_item, str):
                    self._projects['keys'].append({keys_item: {}})
                else:
                    self.log.warning('\'project\' key setting must be a string or a dict: %s', keys_item)
                    raise ConfigurationError('\'project\' key setting must be a string or a dict')
            self.log.debug("projects: %s", self._projects)

    def _validate_default_tag(self):
        self._default_tag = self.instance.get('default_tag', 'component')
        if not isinstance(self._default_tag, str):
            raise ConfigurationError('\'default_tag\' setting must be a string')

    def _validate_default_include(self):
        self._default_include = self.instance.get('default_include', [])
        if not isinstance(self._default_include, list):
            raise ConfigurationError('\'default_include\' setting must be a list')

    def _validate_default_exclude(self):
        self._default_exclude = self.instance.get('default_exclude', [])
        if not isinstance(self._default_exclude, list):
            raise ConfigurationError('\'default_exclude\' setting must be a list')

    def _validate_components(self):
        self.log.debug('validating \'components\': %s', self.instance)
        components = self.instance.get('components', None)
        if components is not None and isinstance(components, dict):
            self.log.debug('\'components\' found in config: %s', components)
            self._projects = {'keys': []}
            default_tag = self.instance.get('default_tag', 'component')
            self.log.debug('default_tag: %s', default_tag)
            self._default_metrics_limit = 100
            self.log.debug('default_metrics_limit: %s', self._default_metrics_limit)
            self._default_metrics_include = [
                self._normalize_pattern(item) for item in self.instance.get('default_include', [])
            ]
            self._default_metrics_include = self._default_metrics_include if self._default_metrics_include else [r'.*']
            self.log.debug('default_metrics_include: %s', self._default_metrics_include)
            self._default_metrics_exclude = [
                self._normalize_pattern(item) for item in self.instance.get('default_exclude', [])
            ]
            self._default_metrics_exclude = self._default_metrics_exclude + [r'^.*\.new_.*']
            self.log.debug('default_metrics_exclude: %s', self._default_metrics_exclude)
            for component_key, component_config in components.items():
                self.log.debug('component_key: %s, component_config: %s', component_key, component_config)
                component_config['tag'] = component_config.get('tag', default_tag)
                component_config['metrics'] = {}
                include = component_config.get('include', None)
                exclude = component_config.get('exclude', None)
                if include or exclude:
                    component_config['metrics']['discovery'] = {}
                    if include is not None:
                        component_config['metrics']['discovery']['include'] = [
                            self._normalize_pattern(item) for item in include
                        ]
                    if exclude is not None:
                        component_config['metrics']['discovery']['exclude'] = [
                            self._normalize_pattern(item) for item in exclude
                        ] + [r'^.*\.new_.*']
                self._projects['keys'].append({component_key: component_config})
            self.log.debug(self._projects)

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

    def _normalize_pattern(self, pattern):
        # Ensure dots are treated as literal
        pattern = pattern.replace('\\.', '.').replace('.', '\\.')
        # Get rid of any explicit start modifiers
        pattern = pattern.lstrip('^')
        # We only search on `<CATEGORY>.<KEY>`
        pattern = re.sub(r'^sonarqube(\\.)?', '', pattern)
        # Match from the start by default
        pattern = '^{}'.format(pattern)
        return pattern

    def collect_metrics(self):
        self.log.debug('collecting metrics')
        projects = self._api.get_projects()
        self.log.debug('%d projects obtained from Sonarqube: %s', len(projects), projects)
        matched_projects = self._projects_discovery_matcher.match(projects)
        self.log.debug('matched_projects: %s', matched_projects)
        if matched_projects:
            all_metrics = self._api.get_metrics()
            self.log.debug('%d metrics obtained from Sonarqube: %s', len(all_metrics), all_metrics)
            for matched_project_key, matched_project_config in matched_projects:
                self._process_project(matched_project_key, matched_project_config, all_metrics)

    def collect_version(self):
        self.log.debug('Collecting version')
        version = self._api.get_version()
        self.log.debug('Sonarqube version: %s', version)
        if not version:
            self.log.warning('The SonarQube version was not found in response')
            return
        # The version comes in like `8.5.0.37579` though sometimes there is no build part
        version_parts = {name: part for name, part in zip(('major', 'minor', 'patch', 'build'), version.split('.'))}
        self.log.debug('Sonarqube version parts: %s', version_parts)
        self.set_metadata('version', version, scheme='parts', final_scheme='semver', part_map=version_parts)

    def _process_project(self, project_key, project_config, all_metrics):
        self.log.debug(
            'processing matched project \'%s\' with config \'%s\'',
            project_key,
            project_config,
        )
        metrics_discovery_matcher = DiscoveryFilter(
            'metrics',
            self.log,
            project_config.get('metrics', {}) if project_config else {},
            mandatory=False,
            default_limit=self._projects.get('default_metrics_limit', self._default_metrics_limit),
            default_include=['({})'.format(item) for item in self._default_metrics_include],
            default_exclude=['({})'.format(item) for item in self._default_metrics_exclude],
        )
        matched_metrics = metrics_discovery_matcher.match(all_metrics)
        self.log.debug('%d matched_metrics: %s', len(matched_metrics), matched_metrics)
        map_metrics_measures = {key.split('.')[1]: key for key, _ in matched_metrics}
        self.log.debug('%d map_metrics_measures: %s', len(map_metrics_measures), map_metrics_measures)
        measures = self._api.get_measures(
            project_key, [key.split('.')[1] for key, _ in matched_metrics]
        )
        self.log.debug(
            '%d measures from project \'%s\' obtained from Sonarqube: %s',
            len(measures),
            project_key,
            measures,
        )
        for measure_key, measure_value in measures:
            mapped_measure = map_metrics_measures.get(measure_key, None)
            if mapped_measure:
                self.gauge(
                    mapped_measure,
                    measure_value,
                    tags=self._tags
                         + [
                             '{}:{}'.format(
                                 project_config.get('tag', self._default_tag)
                                 if project_config
                                 else self._default_tag,
                                 project_key,
                             )
                         ],
                )
            else:
                self.log.warning('\'%s\' not found in matched metrics', measure_key)