# (C) Datadog, Inc. 2014-present
# (C) Paul Kirby <pkirby@matrix-solutions.com> 2014
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

from .common import construct_event, get_response, should_include_build_config
from .constants import (
    DEFAULT_BUILD_CONFIGS_LIMIT,
    SERVICE_CHECK_BUILD_PROBLEMS,
    SERVICE_CHECK_BUILD_STATUS,
    SERVICE_CHECK_TEST_RESULTS,
    STATUS_MAP,
    BuildConfigs,
)
from .metrics import build_metric


class TeamCityCheck(AgentCheck):
    __NAMESPACE__ = 'teamcity'

    HTTP_CONFIG_REMAPPER = {
        'ssl_validation': {'name': 'tls_verify'},
        'headers': {'name': 'headers', 'default': {"Accept": "application/json"}},
    }

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if is_affirmative(instance.get('use_openmetrics', False)):
            if PY2:
                raise ConfigurationError(
                    "This version of the integration is only available when using py3. "
                    "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                    "for more information or use the older style config."
                )
            # TODO: when we drop Python 2 move this import up top
            from .check import TeamCityCheckV2

            return TeamCityCheckV2(name, init_config, instances)
        else:
            return super(TeamCityCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(TeamCityCheck, self).__init__(name, init_config, instances)
        # Legacy configs
        self.build_config = self.instance.get('build_configuration', '')
        self.instance_name = self.instance.get('name', '')
        self.host = self.instance.get('host_affected') or self.hostname
        self.is_deployment = is_affirmative(self.instance.get('is_deployment', False))

        self.monitored_projects = self.instance.get('projects', {})
        self.default_build_configs_limit = self.instance.get('default_build_configs_limit', DEFAULT_BUILD_CONFIGS_LIMIT)
        self.global_build_configs_include = self.instance.get('global_build_configs_include', [])
        self.global_build_configs_exclude = self.instance.get('global_build_configs_exclude', [])
        self.collect_events = is_affirmative(self.instance.get('collect_events', True))
        self.collect_build_metrics = is_affirmative(self.instance.get('build_config_metrics', True))
        self.collect_test_checks = is_affirmative(self.instance.get('test_result_metrics', True))
        self.collect_problem_checks = is_affirmative(self.instance.get('build_problem_checks', True))

        self.basic_http_auth = is_affirmative(self.instance.get('basic_http_authentication', False))
        self.auth_type = 'httpAuth' if self.basic_http_auth else 'guestAuth'
        self.tags = set(self.instance.get('tags', []))
        self.build_tags = []

        server = self.instance.get('server')
        self.server_url = self._normalize_server_url(server)
        self.base_url = "{}/{}".format(self.server_url, self.auth_type)

        instance_tags = [
            'server:{}'.format(self.server_url),
        ]
        if self.instance_name:
            instance_tags.extend(['instance_name:{}'.format(self.instance_name)])
        self.tags.update(instance_tags)

        self.bc_store = BuildConfigs()

        if PY2:
            self.check_initializations.append(self._validate_config)

    def _validate_config(self):
        if self.instance.get('build_configuration') and self.instance.get('projects'):
            raise ConfigurationError('Only one of `projects` or `build_configuration` must be configured, not both.')
        if self.instance.get('build_configuration') is None and self.instance.get('projects') is None:
            raise ConfigurationError('`projects` must be configured.')

    def _normalize_server_url(self, server):
        """
        Check if the server URL starts with an HTTP or HTTPS scheme, fall back to http if not present
        """
        server = server if server.startswith(("http://", "https://")) else "http://{}".format(server)
        return server

    def _initialize(self, project_id=None):
        self.log.debug("Initializing TeamCity builds...")
        # Initialize single build config instance
        if not project_id:
            self.log.debug(
                "Initializing legacy single build configuration monitoring. "
                "To monitor multiple build configurations per check run, use the `projects` option."
            )
            build_config_id = self.build_config
            if not self.bc_store.get_build_config(build_config_id):
                build_config_details = get_response(self, 'build_config', build_conf=build_config_id)

                if build_config_details:
                    project_id = build_config_details.get('projectId')
                    build_config_type = self._get_build_config_type(build_config_id)
                    self.bc_store.set_build_config(build_config_id, project_id, build_config_type)
        else:
            # Initialize multi build config instance
            # Check for new build configs in project
            self.log.debug("Initializing multi-build configuration monitoring.")
            build_configs = get_response(self, 'build_configs', project_id=project_id)
            if build_configs:
                for build_config in build_configs.get('buildType'):
                    build_config_id = build_config['id']
                    if should_include_build_config(
                        self, build_config_id, project_id
                    ) and not self.bc_store.get_build_config(project_id, build_config_id):
                        build_config_type = self._get_build_config_type(build_config['id'])
                        self.bc_store.set_build_config(project_id, build_config_id, build_config_type)
        if self.bc_store.get_build_configs(project_id):
            for build_config in self.bc_store.get_build_configs(project_id):
                if self.bc_store.get_build_config(project_id, build_config):
                    if self.bc_store.get_last_build_id(project_id, build_config) is None:
                        last_build_res = get_response(
                            self, 'last_build', build_conf=build_config, project_id=project_id
                        )
                        if last_build_res:
                            last_build = last_build_res.get('build')[0]
                            last_build_id = last_build.get('id')
                            build_config_id = last_build.get('buildTypeId')

                            self.log.debug(
                                "Last build id for build configuration %s is %s.",
                                build_config_id,
                                last_build_id,
                            )
                            self.bc_store.set_build_config(build_config_id, project_id)
                            self.bc_store.set_last_build_id(project_id, build_config_id, last_build_id)

    def _send_events(self, new_build):
        teamcity_event = construct_event(self, new_build)
        self.log.trace('Submitting event: %s', teamcity_event)
        self.event(teamcity_event)
        self.service_check(
            SERVICE_CHECK_BUILD_STATUS, STATUS_MAP.get(new_build['status'])['check_status'], tags=self.build_tags
        )

    def _collect_build_stats(self, new_build):
        build_id = new_build['id']
        build_stats = get_response(self, 'build_stats', build_id=build_id)

        if build_stats:
            for stat_property in build_stats['property']:
                stat_property_name = stat_property['name']
                metric_name, additional_tags, method = build_metric(stat_property_name)
                if not metric_name or not method:
                    self.log.debug('Found unknown build configuration statistic: %s, skipping.', stat_property_name)
                    continue
                else:
                    metric_value = stat_property['value']
                    method = getattr(self, method)
                    method(metric_name, metric_value, tags=self.build_tags + additional_tags)
        else:
            self.log.debug('No build stats found for build ID: %s.', build_id)

    def _collect_test_results(self, new_build):
        build_id = new_build['id']
        test_results = get_response(self, 'test_occurrences', build_id=build_id)

        if test_results:
            for test in test_results['testOccurrence']:
                test_status = STATUS_MAP[test['status']].get('check_status')
                tags = [
                    'test_status:{}'.format(test['status'].lower()),
                    'test_name:{}'.format(test['name']),
                ]
                self.service_check(SERVICE_CHECK_TEST_RESULTS, test_status, tags=self.build_tags + tags)

    def _collect_build_problems(self, new_build):
        build_id = new_build['id']
        problem_results = get_response(self, 'build_problems', build_id=build_id)

        if problem_results:
            for problem in problem_results['problemOccurrence']:
                problem_type = problem['type']
                problem_identity = problem['identity']
                problem_tags = [
                    'problem_type:{}'.format(problem_type),
                    'problem_identity:{}'.format(problem_identity),
                ]
                self.service_check(
                    SERVICE_CHECK_BUILD_PROBLEMS, AgentCheck.CRITICAL, tags=self.build_tags + problem_tags
                )
        self.service_check(SERVICE_CHECK_BUILD_PROBLEMS, AgentCheck.OK, tags=self.build_tags)

    def _collect_new_builds(self, project_id):
        last_build_id = self.bc_store.get_last_build_id(project_id, self.build_config)
        if last_build_id:
            new_builds = get_response(self, 'new_builds', build_conf=self.build_config, since_build=last_build_id)
            return new_builds
        else:
            self._initialize()

    def _get_build_config_type(self, build_config):
        if self.is_deployment:
            return 'deployment'
        else:
            build_config_settings = get_response(self, 'build_config_settings', build_conf=build_config)
            if build_config_settings:
                for setting in build_config_settings['property']:
                    if setting['name'] == 'buildConfigurationType':
                        build_config_type = setting['value'].lower()
                        return build_config_type
            else:
                self.log.debug(
                    "Could not get build configuration type for %s. Assign `View build configuration settings` to the "
                    "TeamCity user to automatically retrieve and tag metrics by build configuration type."
                )
        return 'build'

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self):
        server_details = get_response(self, 'teamcity_server_details')
        if server_details:
            try:
                version = str(server_details.get('buildDate')[:8])
                build_number = str(server_details['buildNumber'])
                major_version = version[:-4]
                minor_version = version[4:6]
                patch_version = version[-2:]

                version_raw = '{}.{}.{}'.format(version[:-4], version[4:6], version[-2:])

                version_parts = {
                    'major': major_version,
                    'minor': minor_version,
                    'patch': patch_version,
                    'build': build_number,
                }
                self.set_metadata('version', version_raw, scheme='parts', part_map=version_parts)
            except Exception as e:
                self.log.debug("Could not parse version metadata: %s", str(e))
        else:
            self.log.debug("Could not submit version metadata.")

    def _collect(self, project_id):
        new_builds = self._collect_new_builds(project_id)
        if new_builds:
            new_last_build = new_builds['build'][0]
            self.log.debug("Found new builds: %s", [build['buildTypeId'] for build in new_builds['build']])
            self.log.trace("New builds payload: %s", new_builds)
            self.bc_store.set_last_build_id(project_id, self.build_config, new_last_build['id'])

            for build in new_builds['build']:
                stored_build_config = self.bc_store.get_build_config(project_id, self.build_config)
                build_config_type = stored_build_config.build_config_type
                build_tags = list(deepcopy(self.tags))
                build_tags.extend(
                    [
                        'build_config:{}'.format(self.build_config),
                        'project_id:{}'.format(project_id),
                        'type:{}'.format(build_config_type),
                    ]
                )
                self.build_tags = build_tags
                self.log.debug(
                    "New build with id %s (build number: %s), saving and alerting.", build['id'], build['number']
                )
                if self.collect_events:
                    self._send_events(build)
                if self.collect_build_metrics:
                    self._collect_build_stats(build)
                if self.collect_test_checks:
                    self._collect_test_results(build)
                if self.collect_problem_checks:
                    self._collect_build_problems(build)
        else:
            self.log.debug('No new builds found.')

    def check(self, _):
        if self.monitored_projects:
            for project in self.monitored_projects:
                project_id = list(project.keys())[0] if isinstance(project, dict) else project
                if project_id:
                    self._initialize(project_id)
                else:
                    self.log.debug(
                        'Project ID not configured. Refer to Datadog documentation for configuration options.'
                    )
                if self.bc_store.get_build_configs(project_id):
                    for build_config in self.bc_store.get_build_configs(project_id):
                        self.build_config = build_config
                        self._collect(project_id)
        # Single build config instance
        elif self.build_config:
            self._initialize()
            self._collect()

        self._submit_version_metadata()
