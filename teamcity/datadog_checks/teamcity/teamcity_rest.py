# (C) Datadog, Inc. 2014-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.time import get_precise_time

from .build_configs import BuildConfigs
from .common import (
    construct_event,
    filter_build_configs,
    filter_projects,
    get_response,
    normalize_server_url,
    sanitize_server_url,
)
from .constants import (
    DEFAULT_BUILD_CONFIGS_LIMIT,
    DEFAULT_PROJECTS_LIMIT,
    DEFAULT_PROJECTS_REFRESH_INTERVAL,
    SERVICE_CHECK_BUILD_PROBLEMS,
    SERVICE_CHECK_BUILD_STATUS,
    SERVICE_CHECK_TEST_RESULTS,
    STATUS_MAP,
)
from .metrics import build_metric


class TeamCityRest(AgentCheck):
    __NAMESPACE__ = 'teamcity'

    HTTP_CONFIG_REMAPPER = {
        'ssl_validation': {'name': 'tls_verify'},
        'headers': {'name': 'headers', 'default': {"Accept": "application/json"}},
    }

    def __init__(self, name, init_config, instances):
        super(TeamCityRest, self).__init__(name, init_config, instances)
        self.current_build_config = self.instance.get('build_configuration', None)
        self.instance_name = self.instance.get('name', None)
        self.host = self.instance.get('host_affected') or self.hostname
        self.is_deployment = is_affirmative(self.instance.get('is_deployment', False))
        self.basic_http_auth = is_affirmative(
            self.instance.get('basic_http_authentication', bool(self.instance.get('password', False)))
        )

        self.monitored_projects = self.instance.get('projects', {})
        self.default_build_configs_limit = self.instance.get('default_build_configs_limit', DEFAULT_BUILD_CONFIGS_LIMIT)
        self.default_projects_limit = self.instance.get('default_projects_limit', DEFAULT_PROJECTS_LIMIT)
        self.global_build_configs_include = self.instance.get('global_build_configs_include', [])
        self.global_build_configs_exclude = self.instance.get('global_build_configs_exclude', [])
        self.collect_events = is_affirmative(self.instance.get('collect_events', True))
        self.collect_build_metrics = is_affirmative(self.instance.get('build_config_metrics', True))
        self.collect_test_health_checks = is_affirmative(self.instance.get('tests_health_check', True))
        self.collect_build_problem_health_checks = is_affirmative(self.instance.get('build_problem_health_check', True))
        self.projects_refresh_interval = self.instance.get(
            'projects_refresh_interval', DEFAULT_PROJECTS_REFRESH_INTERVAL
        )
        self.projects_last_refresh = None

        self.auth_type = 'httpAuth' if self.basic_http_auth else 'guestAuth'
        self.tags = set(self.instance.get('tags', []))
        self.build_tags = []

        server = self.instance.get('server')
        self.server_url = normalize_server_url(server)
        self.base_url = "{}/{}".format(self.server_url, self.auth_type)

        instance_tags = [
            'server:{}'.format(sanitize_server_url(self.server_url)),
        ]
        if self.instance_name:
            instance_tags.extend(['instance_name:{}'.format(self.instance_name)])
        self.tags.update(instance_tags)

        self.bc_store = BuildConfigs()

        if PY2:
            self.check_initializations.append(self._validate_config)

    def _validate_config(self):
        if self.instance.get('projects'):
            raise ConfigurationError(
                '`projects` option is not supported for Python 2. '
                'Use the `build_configuration` option or upgrade to Python 3.'
            )

    def _get_last_build_id(self, project_id, build_config_id):
        if (
            self.bc_store.get_build_config(project_id, build_config_id)
            and self.bc_store.get_last_build_id(project_id, build_config_id) is None
        ):
            last_build_res = get_response(self, 'last_build', build_conf=build_config_id, project_id=project_id)
            if last_build_res and last_build_res.get('build'):
                last_build = last_build_res.get('build')[0]
                last_build_id = last_build.get('id')

                self.log.debug(
                    "Last build id for build configuration %s is %s.",
                    build_config_id,
                    last_build_id,
                )
                self.bc_store.set_build_config(project_id, build_config_id)
                self.bc_store.set_last_build_id(project_id, build_config_id, last_build_id)

    def _initialize_multi_build_config(self):
        project_ids = [project['id'] for project in get_response(self, 'projects').get('project', [])]
        filtered_projects, projects_limit_reached = filter_projects(self, project_ids)
        if projects_limit_reached:
            self.log.warning(
                "Reached projects limit of %s. Update your `projects` configuration using the `include` and "
                "`exclude` filter options or increase the `default_projects_limit` option.",
                len(filtered_projects),
            )

        for project_id in filtered_projects:
            build_configs_list = [
                build_config['id']
                for build_config in get_response(self, 'build_configs', project_id=project_id).get('buildType', [])
            ]
            # Handle case where the `include` build_config element is a string. Assign `{}` as its filter config.
            # projects:
            #   project_regex:
            #     include:
            #       - build_config_regex
            # `build_config_regex` == `build_config_regex: {}`
            build_config_filter_config = (
                filtered_projects.get(project_id) if isinstance(filtered_projects.get(project_id), dict) else {}
            )
            filtered_build_configs, build_configs_limit_reached = filter_build_configs(
                self, build_configs_list, project_id, build_config_filter_config
            )
            if build_configs_limit_reached:
                self.log.warning(
                    "Reached build configurations limit of %s. Update your `projects` "
                    "configuration using the `include` and `exclude` filter options or "
                    "increase the `default_build_configs_limit` option.",
                    len(filtered_build_configs),
                )
            for build_config_id in filtered_build_configs:
                if not self.bc_store.get_build_config(project_id, build_config_id):
                    build_config_type = self._get_build_config_type(build_config_id)
                    self.bc_store.set_build_config(project_id, build_config_id, build_config_type)
                    self._get_last_build_id(project_id, build_config_id)

    def _initialize_single_build_config(self):
        build_config_id = self.current_build_config
        build_config_details = get_response(self, 'build_config', build_conf=build_config_id)

        if build_config_details and build_config_details.get('projectId'):
            project_id = build_config_details.get('projectId')
            build_config_type = self._get_build_config_type(build_config_id)
            if not self.bc_store.get_build_config(project_id, build_config_id):
                self.bc_store.set_build_config(project_id, build_config_id, build_config_type)
                self._get_last_build_id(project_id, build_config_id)

    def _initialize(self):
        msg = "%s TeamCity projects and build configs..."
        self.log.info(msg, "Re-initializing" if self.projects_last_refresh else "Initializing")
        if not self.monitored_projects and self.current_build_config:
            self.log.debug(
                "Initializing legacy single build configuration monitoring. "
                "To monitor multiple build configurations per check run, use the `projects` option."
            )
            self._initialize_single_build_config()

        else:
            if PY2:
                raise self.CheckException(
                    'Multi-build configuration monitoring is not currently supported in Python 2.'
                )
            self.log.debug("Initializing multi-build configuration monitoring.")
            self._initialize_multi_build_config()

    def _send_events(self, new_build, build_config_type):
        self.log.debug('Sending build event...')
        teamcity_event = construct_event(self, new_build, build_config_type)
        self.log.trace('Submitting event: %s', teamcity_event)
        self.event(teamcity_event)
        self.service_check(
            SERVICE_CHECK_BUILD_STATUS, STATUS_MAP.get(new_build['status'])['check_status'], tags=self.build_tags
        )

    def _collect_build_stats(self, new_build):
        self.log.debug('Collecting build statistics...')
        build_id = new_build['id']
        build_stats = get_response(self, 'build_stats', build_id=build_id)

        if build_stats and build_stats['property']:
            for stat_property in build_stats['property']:
                stat_property_name = stat_property['name']
                metric_name, additional_tags, metric_type = build_metric(stat_property_name)
                if not metric_name or not metric_type:
                    self.log.debug('Found unknown build configuration statistic: %s, skipping.', stat_property_name)
                else:
                    metric_value = stat_property['value']
                    method = getattr(self, metric_type)
                    method(metric_name, metric_value, tags=self.build_tags + additional_tags)
        else:
            self.log.debug('No build stats found for build ID: %s.', build_id)

    def _collect_test_results(self, new_build):
        self.log.debug('Collecting build test results...')
        build_id = new_build['id']
        test_results = get_response(self, 'test_occurrences', build_id=build_id)

        if test_results and test_results['testOccurrence']:
            for test in test_results['testOccurrence']:
                test_status = STATUS_MAP[test['status']].get('check_status')
                tags = [
                    'test_status:{}'.format(test['status'].lower()),
                    'test_name:{}'.format(test['name']),
                ]
                self.service_check(SERVICE_CHECK_TEST_RESULTS, test_status, tags=self.build_tags + tags)

    def _collect_build_problems(self, new_build):
        self.log.debug('Collecting build problems...')
        build_id = new_build['id']
        problem_results = get_response(self, 'build_problems', build_id=build_id)

        if problem_results and problem_results['problemOccurrence']:
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
        last_build_id = self.bc_store.get_last_build_id(project_id, self.current_build_config)
        if not last_build_id:
            self._initialize()
        else:
            self.log.debug('Checking for new builds...')
            new_builds = get_response(
                self, 'new_builds', build_conf=self.current_build_config, since_build=last_build_id
            )
            return new_builds

    def _get_build_config_type(self, build_config):
        if self.is_deployment:
            return 'deployment'
        else:
            build_config_settings = get_response(self, 'build_config_settings', build_conf=build_config)
            if build_config_settings and build_config_settings['property']:
                for setting in build_config_settings['property']:
                    if setting['name'] == 'buildConfigurationType':
                        build_config_type = setting['value'].lower()
                        return build_config_type
            else:
                self.log.warning(
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

    def _collect(self):
        build_configs_store = self.bc_store.get_all_build_configs()
        for project_id in build_configs_store:
            for build_config_id in build_configs_store[project_id]:
                self.current_build_config = build_config_id
                new_builds = self._collect_new_builds(project_id)
                if new_builds and new_builds.get('build'):
                    new_last_build = new_builds['build'][0]
                    self.log.info("Found new builds: %s", [build['buildTypeId'] for build in new_builds['build']])
                    self.log.trace("New builds payload: %s", new_builds)
                    self.bc_store.set_last_build_id(project_id, self.current_build_config, new_last_build['id'])

                    for build in new_builds['build']:
                        stored_build_config = self.bc_store.get_build_config(project_id, self.current_build_config)
                        build_config_type = stored_build_config.build_config_type
                        build_tags = list(deepcopy(self.tags))
                        build_tags.extend(
                            [
                                'build_config:{}'.format(self.current_build_config),
                                'project_id:{}'.format(project_id),
                                'type:{}'.format(build_config_type),
                            ]
                        )
                        self.build_tags = build_tags
                        self.log.debug(
                            "New build with id %s (build number: %s), saving and alerting.",
                            build['id'],
                            build['number'],
                        )
                        if self.collect_events:
                            self._send_events(build, build_config_type)
                        if self.collect_build_metrics:
                            self._collect_build_stats(build)
                        if self.collect_test_health_checks:
                            self._collect_test_results(build)
                        if self.collect_build_problem_health_checks:
                            self._collect_build_problems(build)
                else:
                    self.log.debug('No new builds found.')

    def check(self, _):
        now = get_precise_time()
        if not self.projects_last_refresh or (now - self.projects_last_refresh >= self.projects_refresh_interval):
            self._initialize()
            self.projects_last_refresh = now
        self._collect()
        self._submit_version_metadata()
