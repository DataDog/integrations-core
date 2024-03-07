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

AUTH_BACKEND_CACHE_METRICS = [
    "auth.backend.cache.backend_batch_read_requests.count",
    "auth.backend.cache.backend_batch_read_seconds.bucket",
    "auth.backend.cache.backend_batch_read_seconds.count",
    "auth.backend.cache.backend_batch_read_seconds.sum",
    "auth.backend.cache.backend_batch_write_requests.count",
    "auth.backend.cache.backend_batch_write_seconds.bucket",
    "auth.backend.cache.backend_batch_write_seconds.count",
    "auth.backend.cache.backend_batch_write_seconds.sum",
    "auth.backend.cache.backend_read_requests.count",
    "auth.backend.cache.backend_read_seconds.bucket",
    "auth.backend.cache.backend_read_seconds.count",
    "auth.backend.cache.backend_read_seconds.sum",
    "auth.backend.cache.backend_requests.count",
    "auth.backend.cache.backend_write_requests.count",
    "auth.backend.cache.backend_write_seconds.bucket",
    "auth.backend.cache.backend_write_seconds.count",
    "auth.backend.cache.backend_write_seconds.sum",
    "auth.backend.cache.watcher.event_sizes.count",
    "auth.backend.cache.watcher.event_sizes.sum",
    "auth.backend.cache.watcher.events.bucket",
    "auth.backend.cache.watcher.events.count",
    "auth.backend.cache.watcher.events.sum",
]

AUTH_BACKEND_DYNAMO_METRICS = [
    "auth.backend.dynamo.requests.count",
    "auth.backend.dynamo.requests_seconds.bucket",
    "auth.backend.dynamo.requests_seconds.count",
    "auth.backend.dynamo.requests_seconds.sum",
]

AUTH_BACKEND_FIRESTORE_METRICS = [
    "auth.backend.firestore.events.backend_batch_read_requests.count",
    "auth.backend.firestore.events.backend_batch_read_seconds.bucket",
    "auth.backend.firestore.events.backend_batch_read_seconds.count",
    "auth.backend.firestore.events.backend_batch_read_seconds.sum",
    "auth.backend.firestore.events.backend_batch_write_requests.count",
    "auth.backend.firestore.events.backend_batch_write_seconds.bucket",
    "auth.backend.firestore.events.backend_batch_write_seconds.count",
    "auth.backend.firestore.events.backend_batch_write_seconds.sum",
    "auth.backend.firestore.events.backend_write_requests.count",
    "auth.backend.firestore.events.backend_write_seconds.bucket",
    "auth.backend.firestore.events.backend_write_seconds.count",
    "auth.backend.firestore.events.backend_write_seconds.sum",
]

AUTH_BACKEND_GCP_GCS_METRICS = [
    "auth.backend.gcs.event_storage.downloads_seconds.bucket",
    "auth.backend.gcs.event_storage.downloads_seconds.count",
    "auth.backend.gcs.event_storage.downloads_seconds.sum",
    "auth.backend.gcs.event_storage.downloads.count",
    "auth.backend.gcs.event_storage.uploads_seconds.bucket",
    "auth.backend.gcs.event_storage.uploads_seconds.count",
    "auth.backend.gcs.event_storage.uploads_seconds.sum",
    "auth.backend.gcs.event_storage.uploads.count",
]

AUTH_BACKEND_ETCD_METRICS = [
    "auth.backend.etcd.backend_batch_read_requests.count",
    "auth.backend.etcd.backend_batch_read_seconds.bucket",
    "auth.backend.etcd.backend_batch_read_seconds.count",
    "auth.backend.etcd.backend_batch_read_seconds.sum",
    "auth.backend.etcd.backend_read_requests.count",
    "auth.backend.etcd.backend_read_seconds.bucket",
    "auth.backend.etcd.backend_read_seconds.count",
    "auth.backend.etcd.backend_read_seconds.sum",
    "auth.backend.etcd.backend_tx_requests.count",
    "auth.backend.etcd.backend_tx_seconds.bucket",
    "auth.backend.etcd.backend_tx_seconds.count",
    "auth.backend.etcd.backend_tx_seconds.sum",
    "auth.backend.etcd.backend_write_requests.count",
    "auth.backend.etcd.backend_write_seconds.bucket",
    "auth.backend.etcd.backend_write_seconds.count",
    "auth.backend.etcd.backend_write_seconds.sum",
    "auth.backend.etcd.teleport_etcd_events.count",
    "auth.backend.etcd.teleport_etcd_event_backpressure.count",
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


def test_auth_backend_cache_teleport_metrics(dd_run_check, aggregator, mock_http_response):
    fixtures_path = os.path.join(get_here(), "fixtures", "metrics.txt")
    mock_http_response(file_path=fixtures_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_CACHE_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")


def test_auth_backend_dynamo_teleport_metrics(dd_run_check, aggregator, mock_http_response):
    fixtures_path = os.path.join(get_here(), "fixtures", "metrics.txt")
    mock_http_response(file_path=fixtures_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_DYNAMO_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")


def test_auth_backend_firestore_teleport_metrics(dd_run_check, aggregator, mock_http_response):
    fixtures_path = os.path.join(get_here(), "fixtures", "metrics.txt")
    mock_http_response(file_path=fixtures_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_FIRESTORE_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")


def test_auth_backend_gcp_gcs_teleport_metrics(dd_run_check, aggregator, mock_http_response):
    fixtures_path = os.path.join(get_here(), "fixtures", "metrics.txt")
    mock_http_response(file_path=fixtures_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_GCP_GCS_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")


def test_auth_backend_etcd_teleport_metrics(dd_run_check, aggregator, mock_http_response):
    fixtures_path = os.path.join(get_here(), "fixtures", "metrics.txt")
    mock_http_response(file_path=fixtures_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_ETCD_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
