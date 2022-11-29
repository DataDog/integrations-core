# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests.exceptions import RequestException

from datadog_checks.base import AgentCheck

from .discovery_filter import DiscoveryFilter
from .sonarqube_api import SonarqubeAPI
from .sonarqube_config import SonarqubeConfig


class SonarqubeCheck(AgentCheck):
    __NAMESPACE__ = 'sonarqube'
    SERVICE_CHECK_CONNECT = 'api_access'

    def __init__(self, name, init_config, instances):
        super(SonarqubeCheck, self).__init__(name, init_config, instances)
        self._config = SonarqubeConfig(self.instance, self.log)
        self._projects_discovery_filter = DiscoveryFilter('projects', self.log, self._config.projects)
        self._api = SonarqubeAPI(self.log, self.http, self._config.web_endpoint)

    def check(self, _):
        try:
            self.collect_metadata()
            self.collect_metrics()
        except RequestException as e:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, tags=self._config.tags, message=str(e))
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._config.tags)

    @AgentCheck.metadata_entrypoint
    def collect_metadata(self):
        self.collect_version()

    def collect_metrics(self):
        self.log.debug('collecting metrics')
        projects = self._api.get_projects()
        self.log.debug('%d projects obtained from Sonarqube: %s', len(projects), projects)
        matched_projects = self._projects_discovery_filter.match(projects)
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
        metrics_discovery_filter = DiscoveryFilter(
            'metrics',
            self.log,
            project_config.get('metrics', {}) if project_config else {},
            mandatory=False,
            default_limit=self._config.projects.get('default_metrics_limit', self._config.default_metrics_limit),
            default_include=['({})'.format(item) for item in self._config.default_metrics_include],
            default_exclude=['({})'.format(item) for item in self._config.default_metrics_exclude],
        )
        matched_metrics = metrics_discovery_filter.match(all_metrics)
        self.log.debug('%d matched_metrics: %s', len(matched_metrics), matched_metrics)
        map_metrics_measures = {key.split('.')[1]: key for key, _ in matched_metrics}
        self.log.debug('%d map_metrics_measures: %s', len(map_metrics_measures), map_metrics_measures)
        measures = self._api.get_measures(project_key, [key.split('.')[1] for key, _ in matched_metrics])
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
                    tags=self._config.tags
                    + [
                        '{}:{}'.format(
                            project_config.get('tag', self._config.default_tag)
                            if project_config
                            else self._config.default_tag,
                            project_key,
                        )
                    ],
                )
            else:
                self.log.warning('\'%s\' not found in matched metrics', measure_key)
