# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
DEFAULT_METRICS = {
    'external_dns_registry_endpoints_total': 'registry.endpoints.total',
    'external_dns_source_endpoints_total': 'source.endpoints.total',
    'external_dns_source_errors_total': 'source.errors.total',
    'external_dns_registry_errors_total': 'registry.errors.total',
    'source_errors_total': 'source.errors.total',
    'registry_errors_total': 'registry.errors.total',
    'external_dns_controller_last_sync_timestamp_seconds': 'controller.last_sync',
    'external_dns_controller_consecutive_soft_errors': 'controller.consecutive.soft.errors',
    'external_dns_controller_last_reconcile_timestamp_seconds': 'controller.last_reconcile',
}
