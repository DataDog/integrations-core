# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.jmx import JVM_E2E_METRICS

JMX_METRICS = [
    'sonarqube.server.async_execution.largest_worker_count',
    'sonarqube.server.async_execution.queue_size',
    'sonarqube.server.async_execution.worker_count',
    'sonarqube.server.database.pool_active_connections',
    'sonarqube.server.database.pool_idle_connections',
    'sonarqube.server.database.pool_initial_size',
    'sonarqube.server.database.pool_min_idle_connections',
    'sonarqube.server.database.pool_max_active_connections',
    'sonarqube.server.database.pool_max_idle_connections',
    'sonarqube.server.database.pool_max_wait_millis',
    'sonarqube.server.database.pool_remove_abandoned_timeout_seconds',
]
JMX_METRICS.extend(JVM_E2E_METRICS)

WEB_METRICS = [
    'sonarqube.complexity.cognitive_complexity',
    'sonarqube.complexity.complexity',
    'sonarqube.coverage.coverage',
    'sonarqube.coverage.line_coverage',
    'sonarqube.coverage.lines_to_cover',
    'sonarqube.coverage.uncovered_lines',
    'sonarqube.duplications.duplicated_blocks',
    'sonarqube.duplications.duplicated_files',
    'sonarqube.duplications.duplicated_lines',
    'sonarqube.duplications.duplicated_lines_density',
    'sonarqube.issues.blocker_violations',
    'sonarqube.issues.confirmed_issues',
    'sonarqube.issues.critical_violations',
    'sonarqube.issues.false_positive_issues',
    'sonarqube.issues.info_violations',
    'sonarqube.issues.major_violations',
    'sonarqube.issues.minor_violations',
    'sonarqube.issues.open_issues',
    'sonarqube.issues.reopened_issues',
    'sonarqube.issues.violations',
    'sonarqube.issues.wont_fix_issues',
    'sonarqube.maintainability.code_smells',
    'sonarqube.maintainability.sqale_debt_ratio',
    'sonarqube.maintainability.sqale_rating',
    'sonarqube.reliability.bugs',
    'sonarqube.reliability.reliability_rating',
    'sonarqube.security.security_rating',
    'sonarqube.security.vulnerabilities',
    'sonarqube.size.classes',
    'sonarqube.size.comment_lines',
    'sonarqube.size.comment_lines_density',
    'sonarqube.size.files',
    'sonarqube.size.functions',
    'sonarqube.size.lines',
    'sonarqube.size.ncloc',
    'sonarqube.size.statements',
]

ALL_METRICS = WEB_METRICS + JMX_METRICS
