# (C) Datadog, Inc. 2014-present
# (C) Paul Kirby <pkirby@matrix-solutions.com> 2014
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from copy import deepcopy

from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

from .common import SERVICE_CHECK_STATUS_MAP, BuildConfigs, construct_event, get_response
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
        self.build_config = self.instance.get('build_configuration', None)
        self.instance_name = self.instance.get('name')
        self.host = self.instance.get('host_affected') or self.hostname
        self.is_deployment = is_affirmative(self.instance.get('is_deployment', False))

        self.monitored_build_configs = self.instance.get('projects', {})
        self.collect_events = is_affirmative(self.instance.get('collect_events', True))
        self.collect_build_metrics = is_affirmative(self.instance.get('build_config_metrics', True))
        self.collect_test_metrics = is_affirmative(self.instance.get('test_result_metrics', True))
        self.collect_problem_checks = is_affirmative(self.instance.get('build_problem_checks', True))

        self.basic_http_auth = is_affirmative(self.instance.get('basic_http_authentication', False))
        self.auth_type = 'httpAuth' if self.basic_http_auth else 'guestAuth'
        self.tags = set(self.instance.get('tags', []))

        server = self.instance.get('server')
        self.server_url = self._normalize_server_url(server)
        self.base_url = "{}/{}".format(self.server_url, self.auth_type)

        instance_tags = [
            'server:{}'.format(self.server_url),
            'type:deployment' if self.is_deployment else 'type:build',
        ]
        if self.instance_name:
            instance_tags.extend(['instance_name:{}'.format(self.instance_name)])
        self.tags.update(instance_tags)

        self.bc_store = BuildConfigs()

    def _send_events(self, new_build, build_tags):
        teamcity_event = construct_event(self.is_deployment, self.instance_name, self.host, new_build, build_tags)
        self.log.trace('Submitting event: %s', teamcity_event)
        self.event(teamcity_event)
        self.service_check('build.status', SERVICE_CHECK_STATUS_MAP.get(new_build['status']), tags=build_tags)

    def _initialize(self, project_id=None):
        self.log.debug("Initializing TeamCity builds...")
        # Initialize single build config instance
        if not project_id:
            build_config_id = self.build_config
            if not self.bc_store.get_build_config(build_config_id):
                build_config_details = get_response(self, 'build_config', build_conf=build_config_id)
                project_id = build_config_details['projectId']
                self.bc_store.set_build_config(build_config_id, project_id)
        else:
            # Initialize multi build config instance
            # Check for new build configs in project
            build_configs = get_response(self, 'build_configs', project_id=project_id)
            for build_config in build_configs.get('buildType'):
                if self._should_include_build_config(build_config['id']) and not self.bc_store.get_build_config(
                    build_config['id']
                ):
                    self.bc_store.set_build_config(build_config.get('id'), project_id)

        for build_config in self.bc_store.get_build_configs():
            if self.bc_store.get_build_config(build_config):
                if self.bc_store.get_last_build_id(build_config) is None:
                    last_build_res = get_response(self, 'last_build', build_conf=build_config)

                    last_build_id = last_build_res['build'][0]['id']
                    build_config_id = last_build_res['build'][0]['buildTypeId']

                    self.log.debug(
                        "Last build id for build configuration %s is %s.",
                        build_config_id,
                        last_build_id,
                    )
                    self.bc_store.set_build_config(build_config_id, project_id)
                    self.bc_store.set_last_build_id(build_config_id, last_build_id)

    def _collect_build_stats(self, new_build, build_tags):
        build_id = new_build['id']
        build_stats = get_response(self, 'build_stats', build_conf=self.build_config, build_id=build_id)

        if build_stats:
            for stat_property in build_stats['property']:
                stat_property_name = stat_property['name']
                metric_name, additional_tags, method = build_metric(stat_property_name)
                metric_value = stat_property['value']
                method = getattr(self, method)
                method(metric_name, metric_value, tags=build_tags + additional_tags)

    def _collect_test_results(self, new_build, build_tags):
        build_id = new_build['id']
        test_results = get_response(self, 'test_occurrences', build_id=build_id)

        if test_results:
            for test in test_results['testOccurrence']:
                test_status = test['status']
                value = 1 if test_status == 'SUCCESS' else 0
                tags = [
                    'result:{}'.format(test_status.lower()),
                    'test_name:{}'.format(test['name']),
                ]
                self.gauge('test_result', value, tags=build_tags + tags)

    def _collect_build_problems(self, new_build, build_tags):
        build_id = new_build['id']
        problem_results = get_response(self, 'build_problems', build_id=build_id)

        if problem_results:
            for problem in problem_results['problemOccurrence']:
                problem_type = problem['type']
                problem_identity = problem['identity']
                tags = [
                    'problem_type:{}'.format(problem_type),
                    'problem_identity:{}'.format(problem_identity),
                ]
                self.service_check('build_problem', AgentCheck.WARNING, tags=build_tags + tags)

    def _should_include_build_config(self, build_config):
        """
        Return `True` if the build_config is included, otherwise `False`
        """
        exclude_filter, include_filter = self._construct_build_configs_filter()
        include_match = False
        exclude_match = False
        # If no filters configured, include everything
        if not exclude_filter and not include_filter:
            return True
        if exclude_filter:
            for pattern in exclude_filter:
                if re.search(re.compile(pattern), build_config):
                    exclude_match = True
        if include_filter:
            for pattern in include_filter:
                if re.search(re.compile(pattern), build_config):
                    include_match = True

        # Include everything except in excluded_bc
        if exclude_filter and not include_filter:
            return not exclude_match
        # Include only what's defined in included_bc
        if include_filter and not exclude_filter:
            return include_match
        # If both include and exclude filters are configured
        if include_filter and exclude_filter:
            # If filter overlap or in neither filter, exclude
            if (include_match and exclude_match) or (not include_match and not exclude_match):
                return False
            # Only matches include filter, include
            if include_match and not exclude_match:
                return include_match
            # Only matches exclude filter, exclude
            if exclude_match and not include_match:
                return not exclude_match
        return True

    def _collect_new_builds(self):
        last_build_id = self.bc_store.get_last_build_id(self.build_config)
        if last_build_id:
            new_builds = get_response(self, 'new_builds', build_conf=self.build_config, since_build=last_build_id)
            return new_builds

    def _normalize_server_url(self, server):
        """
        Check if the server URL starts with a HTTP or HTTPS scheme, fall back to http if not present
        """
        server = server if server.startswith(("http://", "https://")) else "http://{}".format(server)
        return server

    def _construct_build_configs_filter(self):
        excluded_build_configs = set()
        included_build_configs = set()
        for project in self.monitored_build_configs:
            config = self.monitored_build_configs.get(project)
            # collect all build configs in project
            if isinstance(config, dict):
                exclude_list = config.get('exclude', [])
                include_list = config.get('include', [])
                if exclude_list:
                    excluded_build_configs.update(exclude_list)
                if include_list:
                    for include_bc in include_list:
                        if include_bc not in excluded_build_configs:
                            included_build_configs.update([include_bc])
            elif config is None:
                continue
            else:
                raise ConfigurationError(
                    "`project` must be either an empty mapping to collect all build configurations in the project"
                    "or a mapping of keys `include` and/or `exclude` lists of build configurations."
                )
        return excluded_build_configs, included_build_configs

    def _collect(self):
        new_builds = self._collect_new_builds()
        if new_builds:
            last_build = new_builds['build'][0]
            self.log.debug("Found new builds: %s", [build['buildTypeId'] for build in new_builds['build']])
            self.log.trace("New builds payload: %s", new_builds)
            self.bc_store.set_last_build_id(self.build_config, last_build['id'])

            for build in new_builds['build']:
                build_tags = list(deepcopy(self.tags))
                build_tags.extend(['build_config:{}'.format(build['buildTypeId'])])
                self.log.debug(
                    "New build with id %s (build number: %s), saving and alerting.", build['id'], build['number']
                )
                if self.collect_events:
                    self._send_events(build, build_tags)
                if self.collect_build_metrics:
                    self._collect_build_stats(build, build_tags)
                if self.collect_test_metrics:
                    self._collect_test_results(build, build_tags)
                if self.collect_problem_checks:
                    self._collect_build_problems(build, build_tags)
        else:
            self.log.debug('No new builds found.')

    def check(self, _):
        # Multi build config instance
        if self.monitored_build_configs:
            for project in self.monitored_build_configs:
                project_id = project.get('name') if isinstance(project, dict) else project
                if project_id:
                    self._initialize(project_id)
            for build_config in self.bc_store.get_build_configs():
                self.build_config = build_config
                self._collect()
        # Single build config instance
        elif self.build_config:
            self._initialize()
            self._collect()
