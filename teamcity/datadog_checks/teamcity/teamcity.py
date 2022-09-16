# (C) Datadog, Inc. 2014-present
# (C) Paul Kirby <pkirby@matrix-solutions.com> 2014
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

from .common import construct_event, get_response, should_include_build_config
from .constants import SERVICE_CHECK_STATUS_MAP, BuildConfigs
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

        self.monitored_build_configs = self.instance.get('projects', {})
        self.collect_events = is_affirmative(self.instance.get('collect_events', True))
        self.collect_build_metrics = is_affirmative(self.instance.get('build_config_metrics', True))
        self.collect_test_metrics = is_affirmative(self.instance.get('test_result_metrics', True))
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
            'type:deployment' if self.is_deployment else 'type:build',
        ]
        if self.instance_name:
            instance_tags.extend(['instance_name:{}'.format(self.instance_name)])
        self.tags.update(instance_tags)

        self.bc_store = BuildConfigs()

    def _normalize_server_url(self, server):
        """
        Check if the server URL starts with a HTTP or HTTPS scheme, fall back to http if not present
        """
        server = server if server.startswith(("http://", "https://")) else "http://{}".format(server)
        return server

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
                if should_include_build_config(self, build_config['id']) and not self.bc_store.get_build_config(
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

    def _send_events(self, new_build):
        teamcity_event = construct_event(self, new_build)
        self.log.trace('Submitting event: %s', teamcity_event)
        self.event(teamcity_event)
        self.service_check('build.status', SERVICE_CHECK_STATUS_MAP.get(new_build['status']), tags=self.build_tags)

    def _collect_build_stats(self, new_build):
        build_id = new_build['id']
        build_stats = get_response(self, 'build_stats', build_conf=self.build_config, build_id=build_id)

        if build_stats:
            for stat_property in build_stats['property']:
                stat_property_name = stat_property['name']
                metric_name, additional_tags, method = build_metric(stat_property_name)
                metric_value = stat_property['value']
                method = getattr(self, method)
                method(metric_name, metric_value, tags=self.build_tags + additional_tags)

    def _collect_test_results(self, new_build):
        build_id = new_build['id']
        test_results = get_response(self, 'test_occurrences', build_id=build_id)

        if test_results:
            for test in test_results['testOccurrence']:
                test_status = SERVICE_CHECK_STATUS_MAP[test['status']]
                tags = [
                    'result:{}'.format(test['status'].lower()),
                    'test_name:{}'.format(test['name']),
                ]
                self.service_check('test.result', test_status, tags=self.build_tags + tags)

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
                self.service_check('build.problem', AgentCheck.WARNING, tags=self.build_tags + problem_tags)
        else:
            self.service_check('build.problem', AgentCheck.OK, tags=self.build_tags)

    def _collect_new_builds(self):
        last_build_id = self.bc_store.get_last_build_id(self.build_config)
        if last_build_id:
            new_builds = get_response(self, 'new_builds', build_conf=self.build_config, since_build=last_build_id)
            return new_builds

    def _collect(self):
        new_builds = self._collect_new_builds()
        if new_builds:
            new_last_build = new_builds['build'][0]
            self.log.debug("Found new builds: %s", [build['buildTypeId'] for build in new_builds['build']])
            self.log.trace("New builds payload: %s", new_builds)
            self.bc_store.set_last_build_id(self.build_config, new_last_build['id'])

            for build in new_builds['build']:
                project_id = self.bc_store.get_build_config(self.build_config).project_id
                build_tags = list(deepcopy(self.tags))
                build_tags.extend(['build_config:{}'.format(self.build_config), 'project_id:{}'.format(project_id)])
                self.build_tags = build_tags
                self.log.debug(
                    "New build with id %s (build number: %s), saving and alerting.", build['id'], build['number']
                )
                if self.collect_events:
                    self._send_events(build)
                if self.collect_build_metrics:
                    self._collect_build_stats(build)
                if self.collect_test_metrics:
                    self._collect_test_results(build)
                if self.collect_problem_checks:
                    self._collect_build_problems(build)
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
