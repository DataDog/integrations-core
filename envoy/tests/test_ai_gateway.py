# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import DEFAULT_INSTANCE, get_fixture_path

pytestmark = [pytest.mark.unit]

ENDPOINT = 'http://localhost:1064/metrics'
INSTANCE = {'ai_gateway_endpoint': ENDPOINT, 'tags': ['env:test']}

ATTEMPT = 'trajectory.profile:gen_ai.client.provider_attempt/0.1.0'
BREAKDOWN = 'trajectory.profile:trajectory.gen_ai.client.token_breakdown/0.1.0'
BASE_TAGS = [f'endpoint:{ENDPOINT}', 'env:test', 'trajectory.observation.point:gateway']
OPENAI_CHAT = [
    *BASE_TAGS,
    'gen_ai.operation.name:chat',
    'gen_ai.provider.name:openai',
    'gen_ai.backend:default/openai',
    'gen_ai.original.model:gpt-4o-mini',
    'gen_ai.request.model:gpt-4o-mini',
]
GPT_4O_MINI = [*OPENAI_CHAT, 'gen_ai.response.model:gpt-4o-mini-2024-07-18']
CLAUDE = [
    *BASE_TAGS,
    'gen_ai.operation.name:chat',
    'gen_ai.provider.name:anthropic',
    'gen_ai.backend:default/anthropic',
    'gen_ai.original.model:claude-sonnet-4-5',
    'gen_ai.request.model:claude-sonnet-4-5',
    'gen_ai.response.model:claude-sonnet-4-5-20250929',
]
GPT_5_NANO = [
    *BASE_TAGS,
    'gen_ai.operation.name:chat',
    'gen_ai.provider.name:openai',
    'gen_ai.backend:default/openai',
    'gen_ai.original.model:gpt-5-nano',
    'gen_ai.request.model:gpt-5-nano',
    'gen_ai.response.model:gpt-5-nano-2025-08-07',
]
BEDROCK = [
    *BASE_TAGS,
    'gen_ai.operation.name:chat',
    'gen_ai.provider.name:aws.bedrock',
    'gen_ai.backend:default/bedrock-anthropic',
    'gen_ai.original.model:anthropic.claude-haiku-4-5',
    'gen_ai.request.model:anthropic.claude-haiku-4-5',
    'gen_ai.response.model:anthropic.claude-haiku-4-5',
]
COMPLETION = [
    *BASE_TAGS,
    'gen_ai.operation.name:text_completion',
    'gen_ai.provider.name:openai',
    'gen_ai.backend:default/openai',
    'gen_ai.original.model:gpt-3.5-turbo-instruct',
    'gen_ai.request.model:gpt-3.5-turbo-instruct',
    'gen_ai.response.model:gpt-3.5-turbo-instruct',
]
EMBEDDINGS = [
    *BASE_TAGS,
    'gen_ai.operation.name:embeddings',
    'gen_ai.provider.name:openai',
    'gen_ai.backend:default/openai',
    'gen_ai.original.model:text-embedding-3-small',
    'gen_ai.request.model:text-embedding-3-small',
    'gen_ai.response.model:text-embedding-3-small',
]
TOKENS = 'envoy.gen_ai.client.inference.usage.'
INPUT = f'{TOKENS}input_tokens'
OUTPUT = f'{TOKENS}output_tokens'
CACHE_READ = f'{TOKENS}cache_read.input_tokens'
CACHE_WRITE = f'{TOKENS}cache_write.input_tokens'
REASONING = f'{TOKENS}reasoning.output_tokens'
UNKNOWN_MODALITY = 'gen_ai.token.modality:unknown'


@pytest.fixture
def ai_gateway_metrics(mock_http_response):
    mock_http_response(file_path=get_fixture_path('ai_gateway/metrics.txt'))


@pytest.mark.usefixtures('ai_gateway_metrics')
def test_token_counts(aggregator, dd_run_check, check):
    """Every token count the gateway reported, and only those, under its spec name, profile and tags."""
    dd_run_check(check(INSTANCE))

    attempt = [ATTEMPT, UNKNOWN_MODALITY]
    breakdown = [BREAKDOWN, UNKNOWN_MODALITY]
    expected = [
        (INPUT, 1250, GPT_4O_MINI + attempt),
        (OUTPUT, 320, GPT_4O_MINI + attempt),
        (CACHE_READ, 1024, GPT_4O_MINI + breakdown),
        (INPUT, 900, GPT_5_NANO + attempt),
        (OUTPUT, 400, GPT_5_NANO + attempt),
        # A reported zero is a valid count.
        (CACHE_READ, 0, GPT_5_NANO + breakdown),
        (REASONING, 128, GPT_5_NANO + breakdown),
        # `messages` and `chat` calls to the same model are both `chat`, so their counts are summed.
        (INPUT, 100, CLAUDE + attempt),
        (OUTPUT, 10, CLAUDE + attempt),
        (CACHE_READ, 40, CLAUDE + breakdown),
        (CACHE_WRITE, 25, CLAUDE + breakdown + ['trajectory.cache.lifetime:unspecified']),
        (INPUT, 500, BEDROCK + attempt),
        (OUTPUT, 100, BEDROCK + attempt),
        (INPUT, 20, COMPLETION + attempt),
        (OUTPUT, 5, COMPLETION + attempt),
        # Embeddings report input only; image generation is not an inference operation.
        (INPUT, 8, EMBEDDINGS + attempt),
    ]
    for name, value, tags in expected:
        aggregator.assert_metric(name, value=value, tags=tags, metric_type=aggregator.MONOTONIC_COUNT, count=1)
    for name in (INPUT, OUTPUT, CACHE_READ, CACHE_WRITE, REASONING):
        aggregator.assert_metric(name, count=sum(1 for e in expected if e[0] == name))


@pytest.mark.usefixtures('ai_gateway_metrics')
def test_latency_distributions(aggregator, dd_run_check, check):
    """Request duration and time to first chunk are distributions with `.sum` and `.count`, under spec tags."""
    dd_run_check(check(INSTANCE))

    duration = 'envoy.gen_ai.client.inference.duration'
    expected_counts = [
        (GPT_4O_MINI, 2),
        (GPT_5_NANO, 1),
        (CLAUDE, 2),
        (BEDROCK, 1),
        (COMPLETION, 1),
        # A failed call has no response model.
        (OPENAI_CHAT + ['error.type:_OTHER'], 1),
    ]
    for tags, count in expected_counts:
        aggregator.assert_metric(
            f'{duration}.count', value=count, tags=tags + [ATTEMPT], metric_type=aggregator.MONOTONIC_COUNT
        )
        aggregator.assert_metric(f'{duration}.sum', tags=tags + [ATTEMPT], metric_type=aggregator.MONOTONIC_COUNT)
    # The spec has no request duration for embeddings.
    aggregator.assert_metric(f'{duration}.count', count=len(expected_counts))
    assert {tuple(sorted(tags + [ATTEMPT])) for tags, _ in expected_counts} == {
        tuple(sorted(d.tags)) for d in aggregator.histogram_bucket(duration)
    }

    ttft = 'envoy.gen_ai.client.inference.time_to_first_chunk'
    for tags in (GPT_5_NANO, CLAUDE):
        aggregator.assert_metric(
            f'{ttft}.count', value=1, tags=tags + [ATTEMPT], metric_type=aggregator.MONOTONIC_COUNT
        )
        aggregator.assert_histogram_bucket(ttft, None, None, None, True, '', tags + [ATTEMPT], at_least=1)


@pytest.mark.usefixtures('ai_gateway_metrics')
def test_metadata(aggregator, dd_run_check, check):
    dd_run_check(check(INSTANCE))

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_with_openmetrics_endpoint(aggregator, dd_run_check, check, mock_http_response_per_endpoint, mock_response):
    """Envoy and Envoy AI Gateway metrics are both collected when both endpoints are set."""
    mock_http_response_per_endpoint(
        {
            DEFAULT_INSTANCE['openmetrics_endpoint']: [
                mock_response(file_path=get_fixture_path('openmetrics/openmetrics.txt'))
            ],
            ENDPOINT: [mock_response(file_path=get_fixture_path('ai_gateway/metrics.txt'))],
        }
    )

    dd_run_check(check({**DEFAULT_INSTANCE, **INSTANCE, 'collect_server_info': False}))

    aggregator.assert_metric('envoy.cluster.upstream_cx_http2.count')
    aggregator.assert_metric(INPUT, value=1250, tags=GPT_4O_MINI + [ATTEMPT, UNKNOWN_MODALITY])
