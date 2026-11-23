# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.teleport import TeleportCheck

from .common import (
    AUTH_AUDIT_LOG_METRICS,
    AUTH_BACKEND_CACHE_METRICS,
    AUTH_BACKEND_DYNAMO_METRICS,
    AUTH_BACKEND_ETCD_METRICS,
    AUTH_BACKEND_FIRESTORE_METRICS,
    AUTH_BACKEND_GCP_GCS_METRICS,
    AUTH_BACKEND_S3_METRICS,
    AUTH_METRICS,
)

pytestmark = [pytest.mark.unit]


def test_auth_teleport_metrics(dd_run_check, aggregator, instance, mock_http_response, metrics_path):
    mock_http_response(file_path=metrics_path)

    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
        aggregator.assert_metric_has_tag(f"teleport.{metric}", "teleport_service:auth")


def test_auth_audit_log_teleport_metrics(dd_run_check, aggregator, instance, mock_http_response, metrics_path):
    mock_http_response(file_path=metrics_path)

    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_AUDIT_LOG_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
        aggregator.assert_metric_has_tag(f"teleport.{metric}", "teleport_service:auth")


def test_auth_backend_s3_teleport_metrics(dd_run_check, aggregator, instance, mock_http_response, metrics_path):
    mock_http_response(file_path=metrics_path)

    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_S3_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
        aggregator.assert_metric_has_tag(f"teleport.{metric}", "teleport_service:auth")


def test_auth_backend_cache_teleport_metrics(dd_run_check, aggregator, instance, mock_http_response, metrics_path):
    mock_http_response(file_path=metrics_path)

    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_CACHE_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
        aggregator.assert_metric_has_tag(f"teleport.{metric}", "teleport_service:auth")


def test_auth_backend_dynamo_teleport_metrics(dd_run_check, aggregator, instance, mock_http_response, metrics_path):
    mock_http_response(file_path=metrics_path)

    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_DYNAMO_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
        aggregator.assert_metric_has_tag(f"teleport.{metric}", "teleport_service:auth")


def test_auth_backend_firestore_teleport_metrics(dd_run_check, aggregator, instance, mock_http_response, metrics_path):
    mock_http_response(file_path=metrics_path)

    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_FIRESTORE_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
        aggregator.assert_metric_has_tag(f"teleport.{metric}", "teleport_service:auth")


def test_auth_backend_gcp_gcs_teleport_metrics(dd_run_check, aggregator, instance, mock_http_response, metrics_path):
    mock_http_response(file_path=metrics_path)

    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_GCP_GCS_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
        aggregator.assert_metric_has_tag(f"teleport.{metric}", "teleport_service:auth")


def test_auth_backend_etcd_teleport_metrics(dd_run_check, aggregator, instance, mock_http_response, metrics_path):
    mock_http_response(file_path=metrics_path)

    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in AUTH_BACKEND_ETCD_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
        aggregator.assert_metric_has_tag(f"teleport.{metric}", "teleport_service:auth")
