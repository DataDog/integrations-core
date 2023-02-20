# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.stubs import aggregator

CERT_METRICS = {
    'cert_manager.certificate.ready_status': aggregator.GAUGE,
    'cert_manager.certificate.expiration_timestamp': aggregator.GAUGE,
}

ACME_METRICS = {
    'cert_manager.http_acme_client.request.count': aggregator.MONOTONIC_COUNT,
    'cert_manager.http_acme_client.request.duration.sum': aggregator.MONOTONIC_COUNT,
    'cert_manager.http_acme_client.request.duration.count': aggregator.MONOTONIC_COUNT,
    'cert_manager.http_acme_client.request.duration.quantile': aggregator.GAUGE,
}

CONTROLLER_METRICS = {
    'cert_manager.clock_time': aggregator.GAUGE,
    'cert_manager.controller.sync_call.count': aggregator.MONOTONIC_COUNT,
}

MOCK_INSTANCE = {
    'openmetrics_endpoint': 'http://fake.tld/prometheus',
}
