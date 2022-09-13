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
            'name': 'TeamCityV2 test build',
            'server': '{}:{}'.format(HOST, PORT),
            'monitored_projects_build_configs': [
                {
                    'name': 'TeamcityPythonFork',
                    'include': ['TeamcityPythonFork_FailedBuild', 'TeamcityPythonFork_FailedTests'],
                    'exclude': ['TeamcityPythonFork_Build'],
                }
            ],
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


PROMETHEUS_METRICS = [
    'teamcity.agents.connected.authorized',
    'teamcity.agents.running.builds',
    'teamcity.build.configs.active',
    'teamcity.build.configs.composite.active',
    'teamcity.build.configs',
    'teamcity.build.messages.incoming.number.count',
    'teamcity.build.messages.processing.number.count',
    'teamcity.build.queue.estimates.processing.number.count',
    'teamcity.build.queue.incoming.number.count',
    'teamcity.build.queue.processing.number.count',
    'teamcity.build.service.messages.number.count',
    'teamcity.builds.finished.number.count',
    'teamcity.builds',
    'teamcity.builds.queued',
    'teamcity.builds.running',
    'teamcity.builds.started.count',
    'teamcity.cpu.count',
    'teamcity.cpu.usage.process',
    'teamcity.cpu.usage.system',
    'teamcity.database.connections.active',
    'teamcity.db.table.writes.number.count',
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
    'teamcity.node.tasks.finished.number.count',
    'teamcity.node.tasks.pending',
    'teamcity.projects.active',
    'teamcity.projects',
    'teamcity.runningBuildsOfUnprocessedMessages',
    'teamcity.server.uptime.milliseconds',
    'teamcity.system.load.average.1m',
    'teamcity.cache.InvestigationTestRunsHolder.projectScopes',
    'teamcity.cache.InvestigationTestRunsHolder.testNames',
    'teamcity.tcache.InvestigationTestRunsHolder.testRuns',
    'teamcity.users.active',
    'teamcity.vcsRootInstances.active',
    'teamcity.vcsRoots',
    'teamcity.vcs.get.current.state.calls.number.count',
]

BUILD_STATS_METRICS = [
    'teamcity.artifacts_size',
    'teamcity.build_duration',
    'teamcity.build_duration.net_time',
    'teamcity.build_test_status',
    'teamcity.inspection_stats_e',
    'teamcity.inspection_stats_w',
    'teamcity.passed_test_count',
    'teamcity.failed_test_count',
    'teamcity.server_side_build_finishing',
    'teamcity.success_rate',
    'teamcity.time_spent_in_queue',
    'teamcity.total_test_count',
    'teamcity.build_stage_duration',
    'teamcity.queue_wait_reason',
]

TEST_OCCURRENCES_METRICS = ['teamcity.test_result']


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)
