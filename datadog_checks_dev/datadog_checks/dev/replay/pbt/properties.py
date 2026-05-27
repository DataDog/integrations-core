# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

PROPERTIES = (
    'deterministic',
    'latest-release-diff',
    'openmetrics-label-order',
    'openmetrics-comments-blank-lines',
    'openmetrics-final-newline',
    'openmetrics-help-text',
    'openmetrics-help-removal',
    'json-object-key-order',
    'json-whitespace',
    'json-string-escapes',
    'metadata-emitted-metrics',
    'repeated-run-tag-stability',
    'openmetrics-coverage',
    'asset-query-metrics-in-metadata',
    'asset-query-tags-seen-in-replay',
    'output-finite-values',
    'rate-finite-values',
    'monotonic-count-nonnegative',
)

PROPERTY_VALIDATION_FAMILIES = {
    'deterministic': 'replay-regression',
    'latest-release-diff': 'replay-regression',
    'metadata-emitted-metrics': 'replay-regression',
    'repeated-run-tag-stability': 'replay-regression',
    'output-finite-values': 'replay-regression',
    'rate-finite-values': 'replay-regression',
    'monotonic-count-nonnegative': 'replay-regression',
    'openmetrics-label-order': 'replay-metamorphic',
    'openmetrics-comments-blank-lines': 'replay-metamorphic',
    'openmetrics-final-newline': 'replay-metamorphic',
    'openmetrics-help-text': 'replay-metamorphic',
    'openmetrics-help-removal': 'replay-metamorphic',
    'json-object-key-order': 'replay-metamorphic',
    'json-whitespace': 'replay-metamorphic',
    'json-string-escapes': 'replay-metamorphic',
    'openmetrics-cache-mutation': 'replay-metamorphic',
    'openmetrics-coverage': 'replay-coverage',
    'asset-query-tags-seen-in-replay': 'replay-coverage',
    'asset-query-metrics-in-metadata': 'static-contract',
}

PROPERTY_REQUIRES_REPLAY_CACHE = {
    property_name: family != 'static-contract'
    for property_name, family in PROPERTY_VALIDATION_FAMILIES.items()
}


def validation_family_for_property(property_name: str | None) -> str:
    return PROPERTY_VALIDATION_FAMILIES.get(property_name or '', 'replay-regression')


def property_requires_replay_cache(property_name: str | None) -> bool:
    return PROPERTY_REQUIRES_REPLAY_CACHE.get(property_name or '', True)
