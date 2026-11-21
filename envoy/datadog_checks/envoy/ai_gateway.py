# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Envoy AI Gateway GenAI metrics, submitted under the Open Trajectory metric names.

Envoy AI Gateway's external processor exposes OpenTelemetry GenAI histograms on its admin
`/metrics` endpoint. This module turns them into the token counts and latency distributions
that Datadog's other LLM gateways submit, so that the same queries work across gateways.
"""

from collections.abc import Callable, Iterable, Iterator

from prometheus_client.samples import Sample

from datadog_checks.base.checks.openmetrics.v2.transformers import get_histogram

PROVIDER_ATTEMPT_PROFILE = 'trajectory.profile:gen_ai.client.provider_attempt/0.1.0'
TOKEN_BREAKDOWN_PROFILE = 'trajectory.profile:trajectory.gen_ai.client.token_breakdown/0.1.0'
OBSERVATION_POINT = 'trajectory.observation.point:gateway'
TOKEN_MODALITY = 'gen_ai.token.modality:unknown'

# Envoy AI Gateway reports this value for a model or provider it did not learn.
UNKNOWN = 'unknown'

# `gen_ai_operation_name` values (one per gateway endpoint) mapped to the spec's inference operations.
# Other operations, such as image generation, rerank or audio, are not inference operations and are skipped.
OPERATIONS = {
    'chat': 'chat',
    'messages': 'chat',
    'responses': 'chat',
    'completion': 'text_completion',
    'embeddings': 'embeddings',
}
TOKEN_OPERATIONS = frozenset(('chat', 'text_completion', 'embeddings'))
DURATION_OPERATIONS = frozenset(('chat', 'text_completion'))

# `gen_ai_provider_name` values that differ from the OpenTelemetry well-known `gen_ai.provider.name`.
# Anthropic models served by Bedrock InvokeModel and Vertex AI rawPredict are billed by those platforms.
PROVIDERS = {
    'azure.openai': 'azure.ai.openai',
    'aws.anthropic': 'aws.bedrock',
    'gcp.anthropic': 'gcp.vertex_ai',
}

# `gen_ai_token_type` values mapped to the metric and tags of their token count. The input count already
# includes cached input, as the spec requires: the gateway adds cache reads and writes to Anthropic's input.
TOKEN_METRICS = {
    'input': ('gen_ai.client.inference.usage.input_tokens', (PROVIDER_ATTEMPT_PROFILE,)),
    'output': ('gen_ai.client.inference.usage.output_tokens', (PROVIDER_ATTEMPT_PROFILE,)),
    'cached_input': ('gen_ai.client.inference.usage.cache_read.input_tokens', (TOKEN_BREAKDOWN_PROFILE,)),
    'cache_creation_input': (
        'gen_ai.client.inference.usage.cache_write.input_tokens',
        # The gateway does not report the cache lifetime of written tokens.
        (TOKEN_BREAKDOWN_PROFILE, 'trajectory.cache.lifetime:unspecified'),
    ),
    'reasoning': ('gen_ai.client.inference.usage.reasoning.output_tokens', (TOKEN_BREAKDOWN_PROFILE,)),
}

SPEC_LABELS = {
    'gen_ai_request_model': 'gen_ai.request.model',
    'gen_ai_response_model': 'gen_ai.response.model',
}

# Labels whose tags are built by `spec_samples`, or which carry no information.
EXCLUDED_LABELS = (
    'gen_ai_operation_name',
    'gen_ai_provider_name',
    'gen_ai_request_model',
    'gen_ai_response_model',
    'gen_ai_token_type',
    'otel_scope_name',
    'otel_scope_schema_url',
    'otel_scope_version',
)

RENAME_LABELS = {
    'error_type': 'error.type',
    'gen_ai_backend': 'gen_ai.backend',
    'gen_ai_original_model': 'gen_ai.original.model',
}

SampleData = Iterable[tuple[Sample, list[str], str]]


def scraper_config(check, instance: dict, endpoint: str) -> dict:
    """The scraper configuration of the `ai_gateway_endpoint`, sharing the instance's HTTP and tag options."""
    config = {key: value for key, value in instance.items() if key not in ('metrics', 'extra_metrics')}
    config['openmetrics_endpoint'] = endpoint
    config['metrics'] = []
    config['exclude_labels'] = [*instance.get('exclude_labels', []), *EXCLUDED_LABELS]
    config['rename_labels'] = {**RENAME_LABELS, **instance.get('rename_labels', {})}
    # Submit each latency histogram as a distribution with its `.sum` and `.count`, as the spec's Datadog binding does,
    # without bucket bound tags on Agents that can drop them.
    config['collect_counters_with_distributions'] = True
    config['collect_histograms_as_distributions'] = check.multiple_histogram_buckets_unsupported_reason() is None
    return config


def spec_samples(sample_data: SampleData, operations: frozenset[str]) -> Iterator[tuple[Sample, list[str], str]]:
    """
    Yield the samples of the given spec operations with spec tags.

    Samples that map to the same tags, such as a `chat` and a `messages` call to the same model, are
    summed: each would otherwise overwrite the other's value in a single context.
    """
    merged = {}
    for sample, tags, hostname in sample_data:
        labels = sample.labels
        operation = OPERATIONS.get(labels.get('gen_ai_operation_name', ''))
        if operation not in operations:
            continue

        provider = labels.get('gen_ai_provider_name', UNKNOWN)
        provider = PROVIDERS.get(provider, provider)
        spec_labels = {**labels, 'gen_ai_operation_name': operation, 'gen_ai_provider_name': provider}
        key = (sample.name, frozenset(spec_labels.items()), hostname)
        if key in merged:
            merged[key][0] += sample.value
            continue

        spec_tags = [*tags, OBSERVATION_POINT, f'gen_ai.operation.name:{operation}']
        if provider != UNKNOWN:
            spec_tags.append(f'gen_ai.provider.name:{provider}')
        for label, tag in SPEC_LABELS.items():
            value = labels.get(label, UNKNOWN)
            if value and value != UNKNOWN:
                spec_tags.append(f'{tag}:{value}')

        merged[key] = [sample.value, sample.name, spec_labels, spec_tags, hostname]

    for value, name, labels, tags, hostname in merged.values():
        yield Sample(name, labels, value), tags, hostname


def token_usage_transformer(check) -> Callable:
    """Submit the `_sum` of `gen_ai_client_token_usage` per token type as a spec token count."""

    def transform(metric, sample_data, runtime_data):
        flush_first_value = runtime_data['flush_first_value']
        for sample, tags, hostname in spec_samples(sample_data, TOKEN_OPERATIONS):
            if not sample.name.endswith('_sum'):
                continue
            token_metric = TOKEN_METRICS.get(sample.labels.get('gen_ai_token_type'))
            if token_metric is None:
                continue
            name, extra_tags = token_metric
            check.monotonic_count(
                name,
                sample.value,
                tags=[*tags, *extra_tags, TOKEN_MODALITY],
                hostname=hostname,
                flush_first_value=flush_first_value,
            )

    return transform


def latency_transformer(check, name: str, operations: frozenset[str], global_options: dict) -> Callable:
    """Submit a latency histogram under a spec name, with spec tags."""
    histogram = get_histogram(check, name, {}, global_options)

    def transform(metric, sample_data, runtime_data):
        samples = (
            (sample, [*tags, PROVIDER_ATTEMPT_PROFILE], hostname)
            for sample, tags, hostname in spec_samples(sample_data, operations)
        )
        histogram(metric, samples, runtime_data)

    return transform


def add_transformers(check, scraper) -> None:
    transformer = scraper.metric_transformer
    transformer.add_custom_transformer('gen_ai_client_token_usage', token_usage_transformer(check))
    transformer.add_custom_transformer(
        'gen_ai_server_request_duration_seconds',
        latency_transformer(check, 'gen_ai.client.inference.duration', DURATION_OPERATIONS, transformer.global_options),
    )
    transformer.add_custom_transformer(
        'gen_ai_server_time_to_first_token_seconds',
        latency_transformer(
            check, 'gen_ai.client.inference.time_to_first_chunk', TOKEN_OPERATIONS, transformer.global_options
        ),
    )
