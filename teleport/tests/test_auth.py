# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import get_here
from datadog_checks.teleport import TeleportCheck

pytestmark = [pytest.mark.unit]

AUTH_METRICS = [
    "auth.generate_requests_throttled.count",
    "auth.generate_requests.count",
    "auth.generate_seconds.bucket",
    "auth.generate_seconds.count",
    "auth.generate_seconds.sum",
    "auth.grpc.server.handled.count",
    "auth.grpc.server.msg_received.count",
    "auth.grpc.server.msg_sent.count",
    "auth.grpc.server.started.count",
    "auth.cluster_name_not_found.count",
    "auth.user.login.count",
    "auth.migrations",
    "auth.watcher.event_sizes.bucket",
    "auth.watcher.event_sizes.count",
    "auth.watcher.event_sizes.sum",
    "auth.watcher.events.bucket",
    "auth.watcher.events.count",
    "auth.watcher.events.sum",
]

AUTH_AUDIT_LOG_METRICS = [
    "auth.audit_log.failed_disk_monitoring.count",
    "auth.audit_log.failed_emit_events.count",
    "auth.audit_log.emit_events.count",
    "auth.audit_log.parquetlog.batch_processing_seconds.bucket",
    "auth.audit_log.parquetlog.batch_processing_seconds.count",
    "auth.audit_log.parquetlog.batch_processing_seconds.sum",
    "auth.audit_log.parquetlog.s3_flush_seconds.bucket",
    "auth.audit_log.parquetlog.s3_flush_seconds.count",
    "auth.audit_log.parquetlog.s3_flush_seconds.sum",
    "auth.audit_log.parquetlog.delete_events_seconds.bucket",
    "auth.audit_log.parquetlog.delete_events_seconds.count",
    "auth.audit_log.parquetlog.delete_events_seconds.sum",
    "auth.audit_log.parquetlog.batch_size.bucket",
    "auth.audit_log.parquetlog.batch_size.count",
    "auth.audit_log.parquetlog.batch_size.sum",
    "auth.audit_log.parquetlog.batch_count.count",
    "auth.audit_log.parquetlog.errors_from_collect_count.count",
]

AUTH_BACKEND_S3_METRICS = [
    "auth.backend.s3.requests.count",
    "auth.backend.s3.requests_seconds.bucket",
    "auth.backend.s3.requests_seconds.count",
    "auth.backend.s3.requests_seconds.sum",
]


def test_auth_teleport_metrics(dd_run_check, aggregator, mock_http_response):
    fixtures_path = os.path.join(get_here(), "fixtures", "metrics.txt")
    mock_http_response(file_path=fixtures_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")


def test_auth_audit_log_teleport_metrics(dd_run_check, aggregator, mock_http_response):
    fixtures_path = os.path.join(get_here(), "fixtures", "metrics.txt")
    mock_http_response(file_path=fixtures_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_AUDIT_LOG_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")


def test_auth_backend_s3_teleport_metrics(dd_run_check, aggregator, mock_http_response):
    fixtures_path = os.path.join(get_here(), "fixtures", "metrics.txt")
    mock_http_response(file_path=fixtures_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_S3_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")