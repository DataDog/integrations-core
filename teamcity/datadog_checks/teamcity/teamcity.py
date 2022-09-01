# (C) Datadog, Inc. 2014-present
# (C) Paul Kirby <pkirby@matrix-solutions.com> 2014
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urlparse

import requests
from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

from .common import (
    BUILD_PROBLEM_OCCURRENCES_URL,
    BUILD_STATS_URL,
    LAST_BUILD_URL,
    NEW_BUILD_URL,
    SERVICE_CHECK_STATUS_MAP,
    TEST_OCCURRENCES_URL,
    construct_event,
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
        self.last_build_ids = {}
        self.instance_name = self.instance.get('name')
        self.host = self.instance.get('host_affected') or self.hostname
        self.build_config = self.instance.get('build_configuration')
        self.is_deployment = is_affirmative(self.instance.get('is_deployment', False))
        self.basic_http_auth = is_affirmative(self.instance.get('basic_http_authentication', False))
        self.auth_type = 'httpAuth' if self.basic_http_auth else 'guestAuth'
        self.tags = set(self.instance.get('tags', []))

        parsed_endpoint = urlparse(self.instance.get('server'))
        self.server_url = "{}://{}".format(parsed_endpoint.scheme, parsed_endpoint.netloc)

        instance_tags = [
            'build_config:{}'.format(self.build_config),
            'server:{}'.format(self.server_url),
            'instance_name:{}'.format(self.instance_name),
            'type:deployment' if self.is_deployment else 'type:build',
        ]
        self.tags.update(instance_tags)

    def _build_and_send_event(self, new_build):
        self.log.debug("Found new build with id %s, saving and alerting.", new_build["number"])
        self.last_build_ids[self.instance_name] = new_build["id"]

        teamcity_event = construct_event(self.is_deployment, self.instance_name, self.host, new_build, list(self.tags))

        self.event(teamcity_event)
        self.service_check('build.status', SERVICE_CHECK_STATUS_MAP.get(new_build['status']), tags=list(self.tags))

    def _initialize(self):
        last_build_id = None
        last_build_url = LAST_BUILD_URL.format(
            server=self.server_url, auth_type=self.auth_type, build_conf=self.build_config
        )
        self.log.debug("Initializing %s", self.instance_name)

        try:
            resp = self.http.get(last_build_url)
            resp.raise_for_status()

            if resp.json()['count'] == 0:
                self.log.debug('No builds found during initialization.')
                return
            else:
                last_build_id = resp.json().get("build")[0].get("number")

        except requests.exceptions.HTTPError:
            if resp.status_code == 401:
                self.log.error("Access denied. Enable guest authentication or check user permissions.")
            self.log.error(
                "Failed to retrieve last build ID with code %s for instance '%s'", resp.status_code, self.instance_name
            )
            raise
        except Exception:
            self.log.exception("Unhandled exception to get last build ID for instance '%s'", self.instance_name)
            raise
        self.log.debug("Last build id for instance %s is %s.", self.instance_name, last_build_id)
        self.last_build_ids[self.instance_name] = last_build_id

    def _collect_build_stats(self, new_build):
        build_id = new_build['id']
        build_stats_url = BUILD_STATS_URL.format(
            server=self.server_url, auth_type=self.auth_type, build_conf=self.build_config, build_id=build_id
        )

        resp = self.http.get(build_stats_url)
        resp.raise_for_status()
        build_stats = resp.json()
        self.log.trace('Build configuration statistics response payload: {}'.format(build_stats))

        for stat_property in build_stats['property']:
            stat_property_name = stat_property['name']
            metric_name, additional_tags, method = build_metric(stat_property_name)
            metric_value = stat_property['value']
            method = getattr(self, method)
            method(metric_name, metric_value, tags=list(self.tags) + additional_tags)

    def _collect_test_results(self, new_build):
        build_id = new_build['id']
        build_number = new_build['number']
        test_occurrences_url = TEST_OCCURRENCES_URL.format(
            server=self.server_url, auth_type=self.auth_type, build_id=build_id
        )

        resp = self.http.get(test_occurrences_url)
        resp.raise_for_status()
        test_results = resp.json()
        self.log.trace('Test occurrences response payload: {}'.format(test_results))
        self.log.debug('Test occurrences response payload: {}'.format(test_results))
        if test_results.get('count') and test_results['count'] > 0:
            for test in test_results['testOccurrence']:
                test_status = test['status']
                value = 1 if test_status == 'SUCCESS' else 0
                tags = [
                    'result:{}'.format(test_status.lower()),
                    'build_number:{}'.format(build_number),
                    'build_id:{}'.format(build_number),
                    'test_name:{}'.format(test['name']),
                ]
                self.gauge('test_result', value, tags=list(self.tags) + tags)

    def _collect_build_problems(self, new_build):
        build_id = new_build['id']
        build_number = new_build['number']
        problem_occurrences_url = BUILD_PROBLEM_OCCURRENCES_URL.format(
            server=self.server_url, auth_type=self.auth_type, build_id=build_id
        )

        resp = self.http.get(problem_occurrences_url)
        resp.raise_for_status()
        problem_results = resp.json()
        self.log.trace('Problem occurrences response payload: {}'.format(problem_results))
        self.log.debug('Problem occurrences response payload: {}'.format(problem_results))
        if problem_results.get('count') and problem_results['count'] > 0:
            for problem in problem_results['problemOccurrence']:
                problem_type = problem['type']
                problem_identity = problem['identity']
                tags = [
                    f'problem_type:{problem_type}',
                    f'problem_identity:{problem_identity}',
                    f'build_id:{build_id}',
                    f'build_number:{build_number}',
                ]
                self.service_check('build_problem', AgentCheck.WARNING, tags=list(self.tags) + tags)

    def check(self, _):
        if not self.last_build_ids.get(self.instance_name):
            self._initialize()

        new_build_url = NEW_BUILD_URL.format(
            server=self.server_url,
            auth_type=self.auth_type,
            build_conf=self.build_config,
            since_build=self.last_build_ids[self.instance_name],
        )
        try:
            resp = self.http.get(new_build_url)
            resp.raise_for_status()
            new_builds = resp.json()

            if new_builds["count"] == 0:
                self.log.debug("No new builds found.")
            else:
                self.log.trace("New builds found: {}".format(new_builds))
                for build in new_builds['build']:
                    self._build_and_send_event(build)
                    self._collect_build_stats(build)
                    self._collect_test_results(build)
                    self._collect_build_problems(build)
        except requests.exceptions.HTTPError:
            self.log.exception("Couldn't fetch last build, got code %s", resp.status_code)
            raise
        except Exception:
            self.log.exception("Couldn't fetch last build, unhandled exception")
            raise
