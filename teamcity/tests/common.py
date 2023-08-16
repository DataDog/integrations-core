# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', '{}', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = '8111'
SERVER_URL = "http://{}:{}".format(HOST, PORT)
CHECK_NAME = 'teamcity'
METRIC_ENDPOINT = '{}/guestAuth/app/metrics'.format(SERVER_URL)

USE_OPENMETRICS = is_affirmative(os.environ.get('USE_OPENMETRICS'))

LEGACY_REST_INSTANCE = {
    'name': 'SampleProject_Build',
    'server': SERVER_URL,
    'build_configuration': 'SampleProject_Build',
    'host_affected': 'buildhost42.dtdg.co',
    'tags': ['build_env:test', 'test_tag:ci_builds'],
}

REST_INSTANCE = {
    'server': SERVER_URL,
    'host_affected': 'buildhost42.dtdg.co',
    'projects': {
        'include': [
            {
                'SampleProject': {
                    'include': [
                        'SampleProject_*',
                    ],
                    'exclude': [
                        'SampleProject_SkippedBuild',
                    ],
                }
            }
        ]
    },
    'tags': ['build_env:test', 'test_tag:ci_builds'],
}

REST_INSTANCE_ALL_PROJECTS = {
    'server': SERVER_URL,
    'host_affected': 'buildhost42.dtdg.co',
    'projects': {},
    'tags': ['build_env:test', 'test_tag:ci_builds'],
}

OPENMETRICS_INSTANCE = {
    'server': 'http://localhost:8111',
    'use_openmetrics': True,
}

CONFIG_BAD_FORMAT = {}

CONFIG_ALL_PROJECTS = {"projects": {}}

CONFIG_MULTIPLE_PROJECTS_MAPPING = {"projects": {"include": [{"project1.*": {}}, {"project2.*": {}}]}}

CONFIG_ONLY_EXCLUDE_ONE_PROJECT = {"projects": {"exclude": [{"project1.*\\.dev": {}}]}}

CONFIG_ALL_BUILD_CONFIGS = {"projects": {"include": [{"project1.*\\.prod": {}}]}}

CONFIG_INCLUDE_MULTIPLE_BUILD_CONFIGs = {
    "projects": {"include": [{"project1.*\\.prod": {"include": ["build_config1", "build_config2"]}}]}
}

CONFIG_ALL_BUILD_CONFIGS_WITH_LIMIT = {"projects": {"include": [{"project1.*\\.prod": {"limit": 3}}]}}

CONFIG_ONLY_INCLUDE_ONE_BUILD_CONFIG = {"build_configs": {"include": ["build_config1.*\\.prod"]}}

CONFIG_ONLY_EXCLUDE_ONE_BUILD_CONFIG = {"build_configs": {"exclude": ["build_config1.*\\.dev"]}}

CONFIG_FILTERING_BUILD_CONFIGS = {
    "global_build_configs_include": ["build_config.*"],
    "global_build_configs_exclude": ["build_config1*.dev"],
    "default_projects_limit": 5,
    "default_build_configs_limit": 5,
    "projects": {
        "include": [
            {
                "project1.*\\.prod": {
                    "build_configs": {"limit": 3, "include": ["build_config.*"], "exclude": ["build_config.prod"]}
                }
            }
        ]
    },
}

CONFIG_FILTERING_PROJECTS = {
    "projects": {"include": [{'project1.*': {}}, {'project2.*': {}}], "exclude": [{'.*tmp': {}}]}
}

# A path regularly used in the TeamCity Check
COMMON_PATH = "guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:1,status:SUCCESS"


# These values are acceptable URLs
TEAMCITY_SERVER_VALUES = {
    # Regular URLs
    "localhost:8111/httpAuth": "http://localhost:8111/httpAuth",
    "localhost:8111/{}".format(COMMON_PATH): "http://localhost:8111/{}".format(COMMON_PATH),
    "http.com:8111/{}".format(COMMON_PATH): "http://http.com:8111/{}".format(COMMON_PATH),
    "http://localhost:8111/some_extra_url_with_http://": "http://localhost:8111/some_extra_url_with_http://",
    "https://localhost:8111/correct_url_https://": "https://localhost:8111/correct_url_https://",
    "https://localhost:8111/{}".format(COMMON_PATH): "https://localhost:8111/{}".format(COMMON_PATH),
    "http://http.com:8111/{}".format(COMMON_PATH): "http://http.com:8111/{}".format(COMMON_PATH),
    # <user>:<password>@teamcity.company.com
    "user:password@localhost:8111/http://_and_https://": "http://user:password@localhost:8111/http://_and_https://",
    "user:password@localhost:8111/{}".format(COMMON_PATH): "http://user:password@localhost:8111/{}".format(COMMON_PATH),
    "http://user:password@localhost:8111/{}".format(COMMON_PATH): "http://user:password@localhost:8111/{}".format(
        COMMON_PATH
    ),
    "https://user:password@localhost:8111/{}".format(COMMON_PATH): "https://user:password@localhost:8111/{}".format(
        COMMON_PATH
    ),
}

BUILD_TAGS = [
    'server:http://localhost:8111',
    'type:build',
    'build_config:SampleProject_Build',
    'project_id:SampleProject',
    'build_env:test',
    'test_tag:ci_builds',
]

REST_METRICS = [
    'teamcity.artifacts_size',
    'teamcity.build_duration',
    'teamcity.build_duration.net_time',
    'teamcity.build_stage_duration',
    'teamcity.build_test_status',
    'teamcity.code_coverage.blocks.covered',
    'teamcity.code_coverage.blocks.pct',
    'teamcity.code_coverage.blocks.total',
    'teamcity.code_coverage.branches.covered',
    'teamcity.code_coverage.branches.pct',
    'teamcity.code_coverage.branches.total',
    'teamcity.code_coverage.classes.covered',
    'teamcity.code_coverage.classes.pct',
    'teamcity.code_coverage.classes.total',
    'teamcity.code_coverage.lines.covered',
    'teamcity.code_coverage.lines.pct',
    'teamcity.code_coverage.lines.total',
    'teamcity.code_coverage.methods.covered',
    'teamcity.code_coverage.methods.pct',
    'teamcity.code_coverage.methods.total',
    'teamcity.code_coverage.statements.covered',
    'teamcity.code_coverage.statements.pct',
    'teamcity.code_coverage.statements.total',
    'teamcity.duplicator_stats',
    'teamcity.failed_test_count',
    'teamcity.passed_test_count',
    'teamcity.ignored_test_count',
    'teamcity.inspection_stats_e',
    'teamcity.inspection_stats_w',
    'teamcity.queue_wait_reason',
    'teamcity.server_side_build_finishing',
    'teamcity.success_rate',
    'teamcity.time_spent_in_queue',
    'teamcity.total_test_count',
]

PROMETHEUS_METRICS = [
    'teamcity.agents.connected.authorized',
    'teamcity.agents.running.builds',
    'teamcity.build.configs.active',
    'teamcity.build.configs.composite.active',
    'teamcity.build.configs',
    'teamcity.build.messages.incoming.count',
    'teamcity.build.messages.processing.count',
    'teamcity.build.queue.estimates.processing.count',
    'teamcity.build.queue.incoming.count',
    'teamcity.build.queue.processing.count',
    'teamcity.build.service.messages.count',
    'teamcity.builds.finished.count',
    'teamcity.builds',
    'teamcity.builds.queued',
    'teamcity.builds.running',
    'teamcity.builds.started.count',
    'teamcity.cpu.count',
    'teamcity.cpu.usage.process',
    'teamcity.cpu.usage.system',
    'teamcity.database.connections.active',
    'teamcity.db.table.writes.count',
    'teamcity.disk_usage.artifacts.bytes',
    'teamcity.disk_usage.logs.bytes',
    'teamcity.executors.asyncXmlRpc.activeTasks',
    'teamcity.executors.asyncXmlRpc.completedTasks',
    'teamcity.executors.asyncXmlRpc.maxQueueCapacity',
    'teamcity.executors.asyncXmlRpc.poolSize',
    'teamcity.executors.asyncXmlRpc.queuedTasks',
    'teamcity.executors.asyncXmlRpc.rejectsCount',
    'teamcity.executors.baseVcsExecutor.activeTasks',
    'teamcity.executors.baseVcsExecutor.completedTasks',
    'teamcity.executors.baseVcsExecutor.maxQueueCapacity',
    'teamcity.executors.baseVcsExecutor.poolSize',
    'teamcity.executors.baseVcsExecutor.queuedTasks',
    'teamcity.executors.baseVcsExecutor.rejectsCount',
    'teamcity.executors.cleanupExecutor.activeTasks',
    'teamcity.executors.cleanupExecutor.completedTasks',
    'teamcity.executors.cleanupExecutor.maxQueueCapacity',
    'teamcity.executors.cleanupExecutor.poolSize',
    'teamcity.executors.cleanupExecutor.queuedTasks',
    'teamcity.executors.cleanupExecutor.rejectsCount',
    'teamcity.executors.lowPriorityExecutor.activeTasks',
    'teamcity.executors.lowPriorityExecutor.completedTasks',
    'teamcity.executors.lowPriorityExecutor.maxQueueCapacity',
    'teamcity.executors.lowPriorityExecutor.poolSize',
    'teamcity.executors.lowPriorityExecutor.queuedTasks',
    'teamcity.executors.lowPriorityExecutor.rejectsCount',
    'teamcity.executors.normalExecutor.activeTasks',
    'teamcity.executors.normalExecutor.completedTasks',
    'teamcity.executors.normalExecutor.maxQueueCapacity',
    'teamcity.executors.normalExecutor.poolSize',
    'teamcity.executors.normalExecutor.queuedTasks',
    'teamcity.executors.normalExecutor.rejectsCount',
    'teamcity.executors.periodicalVcsExecutor.activeTasks',
    'teamcity.executors.periodicalVcsExecutor.completedTasks',
    'teamcity.executors.periodicalVcsExecutor.maxQueueCapacity',
    'teamcity.executors.periodicalVcsExecutor.poolSize',
    'teamcity.executors.periodicalVcsExecutor.queuedTasks',
    'teamcity.executors.periodicalVcsExecutor.rejectsCount',
    'teamcity.executors.tomcatHttpThreadPool.activeTasks',
    'teamcity.executors.tomcatHttpThreadPool.poolSize',
    'teamcity.executors.triggersExecutor.activeTasks',
    'teamcity.executors.triggersExecutor.completedTasks',
    'teamcity.executors.triggersExecutor.maxQueueCapacity',
    'teamcity.executors.triggersExecutor.poolSize',
    'teamcity.executors.triggersExecutor.queuedTasks',
    'teamcity.executors.triggersExecutor.rejectsCount',
    'teamcity.httpSessions.active',
    'teamcity.io.build.log.reads.bytes.count',
    'teamcity.io.build.log.writes.bytes.count',
    'teamcity.io.build.patch.writes.bytes.count',
    'teamcity.jvm.buffers_count',
    'teamcity.jvm.buffer.memory.used.bytes',
    'teamcity.jvm.buffer.total.capacity.bytes',
    'teamcity.jvm.gc.count',
    'teamcity.jvm.gc.duration.total.milliseconds',
    'teamcity.jvm.gc.live.data.size.bytes',
    'teamcity.jvm.gc.max.data.size.bytes',
    'teamcity.jvm.gc.memory.allocated.bytes.count',
    'teamcity.jvm.gc.memory.promoted.bytes.count',
    'teamcity.jvm.memory.committed.bytes',
    'teamcity.jvm.memory.max.bytes',
    'teamcity.jvm.memory.used.bytes',
    'teamcity.jvm.threads.daemon',
    'teamcity.jvm.threads',
    'teamcity.node.events.unprocessed',
    'teamcity.node.tasks.accepted.count',
    'teamcity.node.tasks.finished.count',
    'teamcity.node.tasks.pending',
    'teamcity.projects.active',
    'teamcity.projects',
    'teamcity.runningBuilds.UnprocessedMessages',
    'teamcity.server.uptime.milliseconds',
    'teamcity.system.load.average.1m',
    'teamcity.cache.InvestigationTestRunsHolder.projectScopes',
    'teamcity.cache.InvestigationTestRunsHolder.testNames',
    'teamcity.cache.InvestigationTestRunsHolder.testRuns',
    'teamcity.users.active',
    'teamcity.vcsRootInstances.active',
    'teamcity.vcsRoots',
    'teamcity.vcs.get.current.state.calls.count',
    'teamcity.building_hosted_agents',
    'teamcity.cloud.active_nodes',
    'teamcity.cloud.agent.active_duration_afterBuild',
    'teamcity.cloud.agent.active_duration_beforeBuild',
    'teamcity.cloud.agent.active_duration_betweenBuilds',
    'teamcity.cloud.agent.idle_duration',
    'teamcity.cloud.agent.starting_duration_beforeRegister',
    'teamcity.cloud.agent.total_build_duration',
    'teamcity.cloud.agent.total_build_duration_beforeFinish',
    'teamcity.cloud.build_stuck_canceled',
    'teamcity.cloud.images',
    'teamcity.cloud.plugins.failed_loading.count',
    'teamcity.cloud.server.gc_usage_exceeded_errors',
    'teamcity.cloud.server.high_total_memory_errors',
    'teamcity.cloud.tcc_plugin_loaded',
    'teamcity.current_full_agent_wait_instances',
    'teamcity.current_full_agent_wait_time_max',
    'teamcity.current_full_agent_wait_time_total',
    'teamcity.full_agent_wait_time.quantile',
    'teamcity.node.events.processing.count',
    'teamcity.node.events.publishing.count',
    'teamcity.http.requests.duration.milliseconds.bucket',
    'teamcity.http.requests.duration.milliseconds.count',
    'teamcity.process.queue.milliseconds.count',
    'teamcity.process.queue.parts.milliseconds.count',
    'teamcity.process.websocket.send.pending.messages.milliseconds.count',
    'teamcity.pullRequests.batch.time.milliseconds.count',
    'teamcity.pullRequests.single.time.milliseconds.count',
    'teamcity.vcsChangesCollection.delay.milliseconds.count',
    'teamcity.build.queue.optimization.time.milliseconds.count',
    'teamcity.build.triggers.execution.milliseconds.count',
    'teamcity.build.triggers.per.type.execution.milliseconds.count',
    'teamcity.finishingBuild.buildFinishDelay.milliseconds.count',
    'teamcity.full.agent.waiting.time.milliseconds.count',
    'teamcity.queuedBuild.waitingTime.milliseconds.count',
    'teamcity.startingBuild.buildStartDelay.milliseconds.count',
    'teamcity.startingBuild.runBuildDelay.milliseconds.count',
    'teamcity.vcs.changes.checking.milliseconds.count',
    'teamcity.vcs.git.fetch.duration.milliseconds.count',
]


BUILD_STATS_METRICS = [
    {'name': 'teamcity.artifacts_size', 'value': 47339.0, 'tags': BUILD_TAGS},
    {'name': 'teamcity.inspection_stats_e', 'value': 0.0, 'tags': BUILD_TAGS},
    {'name': 'teamcity.inspection_stats_w', 'value': 0.0, 'tags': BUILD_TAGS},
    {'name': 'teamcity.success_rate', 'value': 0.0, 'tags': BUILD_TAGS},
    {'name': 'teamcity.time_spent_in_queue', 'value': 10.0, 'tags': BUILD_TAGS},
    {'name': 'teamcity.build_duration.net_time', 'value': 11403.0, 'tags': BUILD_TAGS},
    {'name': 'teamcity.total_test_count', 'value': 2.0, 'tags': BUILD_TAGS},
    {'name': 'teamcity.passed_test_count', 'value': 1.0, 'tags': BUILD_TAGS},
    {'name': 'teamcity.failed_test_count', 'value': 1.0, 'tags': BUILD_TAGS},
    {'name': 'teamcity.build_test_status', 'value': 3.0, 'tags': BUILD_TAGS},
    {'name': 'teamcity.build_duration', 'value': 11840.0, 'tags': BUILD_TAGS},
    {'name': 'teamcity.server_side_build_finishing', 'value': 9, 'tags': BUILD_TAGS},
    {'name': 'teamcity.build_stage_duration', 'value': 118.0, 'tags': BUILD_TAGS + ['build_stage:sourcesUpdate']},
    {'name': 'teamcity.build_stage_duration', 'value': 6132.0, 'tags': BUILD_TAGS + ['build_stage:buildStepRUNNER_1']},
    {'name': 'teamcity.build_stage_duration', 'value': 5271.0, 'tags': BUILD_TAGS + ['build_stage:buildStepRUNNER_2']},
    {'name': 'teamcity.code_coverage.blocks.covered', 'value': 90, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.blocks.pct', 'value': 90, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.blocks.total', 'value': 87, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.branches.covered', 'value': 65, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.branches.pct', 'value': 70, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.branches.total', 'value': 88, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.classes.covered', 'value': 65, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.classes.pct', 'value': 87, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.classes.total', 'value': 88, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.lines.covered', 'value': 70, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.lines.pct', 'value': 65, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.lines.total', 'value': 56, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.methods.covered', 'value': 90, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.methods.pct', 'value': 88, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.methods.total', 'value': 87, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.statements.covered', 'value': 70, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.statements.pct', 'value': 56, 'tags': BUILD_TAGS},
    {'name': 'teamcity.code_coverage.statements.total', 'value': 56, 'tags': BUILD_TAGS},
    {'name': 'teamcity.duplicator_stats', 'value': 2, 'tags': BUILD_TAGS},
    {'name': 'teamcity.ignored_test_count', 'value': 3, 'tags': BUILD_TAGS},
    {'name': 'teamcity.visible_artifacts_size', 'value': 389, 'tags': BUILD_TAGS},
    {
        'name': 'teamcity.queue_wait_reason',
        'value': 10.0,
        'tags': BUILD_TAGS + ['reason:Build_settings_have_not_been_finalized'],
    },
    {
        'name': 'teamcity.queue_wait_reason',
        'value': 20.0,
        'tags': BUILD_TAGS + ['reason:Waiting_for_the_build_queue_distribution_process'],
    },
]


EXPECTED_SERVICE_CHECK_TEST_RESULTS = [
    {'value': 0, 'tags': BUILD_TAGS + ['test_status:success', 'test_name:tests.test_foo.test_bar']},
    {'value': 2, 'tags': BUILD_TAGS + ['test_status:failure', 'test_name:tests.test_foo.test_bop']},
    {'value': 0, 'tags': BUILD_TAGS + ['test_status:normal', 'test_name:tests.test_bar.test_foo']},
    {'value': 3, 'tags': BUILD_TAGS + ['test_status:unknown', 'test_name:tests.test_bar.test_zip']},
    {'value': 2, 'tags': BUILD_TAGS + ['test_status:error', 'test_name:tests.test_bar.test_zap']},
    {'value': 1, 'tags': BUILD_TAGS + ['test_status:warning', 'test_name:tests.test_zip.test_bar']},
]


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)
