# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = '8111'
SERVER_URL = "http://{}:{}".format(HOST, PORT)
CHECK_NAME = 'teamcity'

USE_OPENMETRICS = os.getenv('USE_OPENMETRICS')

CONFIG = {
    'instances': [
        {
            'name': 'Legacy test build',
            'server': '{}:{}'.format(HOST, PORT),
            'build_configuration': 'TestProject_TestBuild',
            'host_affected': 'buildhost42.dtdg.co',
            'basic_http_authentication': False,
            'is_deployment': False,
            'tags': ['one:tag', 'one:test'],
        },
        {
            'server': '{}:{}'.format(HOST, PORT),
            'projects': {
                'TeamCityV2Project': {
                    'include': [
                        'TeamCityV2Project_Build',
                        'TeamCityV2Project_FailedBuild',
                        'TeamCityV2Project_FailedTests',
                    ],
                    'exclude': ['TeamCityV2Project_TestBuild'],
                }
            },
            'basic_http_authentication': False,
            'is_deployment': False,
            'tags': ['build_env:test', 'test_tag:ci_builds'],
        },
        {
            'server': 'http://localhost:8111',
            'use_openmetrics': True,
            'basic_http_authentication': False,
        },
    ]
}


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


LEGACY_BUILD_TAGS = [
    'server:http://localhost:8111',
    'type:build',
    'build_config:TestProject_TestBuild',
    'project_id:TestProject',
    'instance_name:Legacy test build',
    'one:test',
    'one:tag',
]

BUILD_TAGS = [
    'server:http://localhost:8111',
    'type:build',
    'build_config:TeamCityV2Project_Build',
    'project_id:TeamCityV2Project',
    'instance_name:TeamCityV2_test_build',
    'build_env:test',
    'test_tag:ci_builds',
]

NEW_SUCCESSFUL_BUILD = {
    'id': 232,
    'buildTypeId': 'TeamCityV2Project_Build',
    'number': '11',
    'status': 'SUCCESS',
    'state': 'finished',
    'branchName': 'main',
    'defaultBranch': True,
    'href': '/guestAuth/app/rest/builds/id:232',
    'webUrl': 'http://localhost:8111/viewLog.html?buildId=232&buildTypeId=TeamCityV2Project_Build',
    'finishOnAgentDate': '20220913T210820+0000',
}

NEW_FAILED_BUILD = {
    'id': 233,
    'buildTypeId': 'TeamCityV2Project_FailedBuild',
    'number': '12',
    'status': 'FAILURE',
    'state': 'finished',
    'branchName': 'main',
    'defaultBranch': True,
    'href': '/guestAuth/app/rest/builds/id:233',
    'webUrl': 'http://localhost:8111/viewLog.html?buildId=233&buildTypeId=TeamCityV2Project_FailedBuild',
    'finishOnAgentDate': '20220913T210826+0000',
}

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
    'teamcity.jvm.buffer.count',
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


TESTS_SERVICE_CHECK_RESULTS = [
    {'value': 0, 'tags': BUILD_TAGS + ['test_status:success', 'test_name:tests.test_foo.test_bar']},
    {'value': 2, 'tags': BUILD_TAGS + ['test_status:failure', 'test_name:tests.test_foo.test_bop']},
    {'value': 0, 'tags': BUILD_TAGS + ['test_status:normal', 'test_name:tests.test_bar.test_foo']},
    {'value': 3, 'tags': BUILD_TAGS + ['test_status:unknown', 'test_name:tests.test_bar.test_zip']},
    {'value': 2, 'tags': BUILD_TAGS + ['test_status:error', 'test_name:tests.test_bar.test_zap']},
    {'value': 1, 'tags': BUILD_TAGS + ['test_status:warning', 'test_name:tests.test_zip.test_bar']},
]
