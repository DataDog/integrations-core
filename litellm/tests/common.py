# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()

OM_MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://litellm:4000/metrics',
    'tags': ['test:tag'],
}


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


METRICS = [
    'litellm.api.key.budget.remaining_hours.metric',
    'litellm.api.key.max_budget.metric',
    'litellm.auth.failed_requests.count',
    'litellm.auth.latency.bucket',
    'litellm.auth.latency.count',
    'litellm.auth.latency.sum',
    'litellm.auth.total_requests.count',
    'litellm.batch_write_to_db.failed_requests.count',
    'litellm.batch_write_to_db.latency.bucket',
    'litellm.batch_write_to_db.latency.count',
    'litellm.batch_write_to_db.latency.sum',
    'litellm.batch_write_to_db.total_requests.count',
    'litellm.deployment.cooled_down.count',
    'litellm.deployment.failed_fallbacks.count',
    'litellm.deployment.failure_by_tag_responses.count',
    'litellm.deployment.failure_responses.count',
    'litellm.deployment.latency_per_output_token.bucket',
    'litellm.deployment.latency_per_output_token.count',
    'litellm.deployment.latency_per_output_token.sum',
    'litellm.deployment.state',
    'litellm.deployment.success_responses.count',
    'litellm.deployment.successful_fallbacks.count',
    'litellm.deployment.total_requests.count',
    'litellm.in_memory.daily_spend_update_queue.size',
    'litellm.in_memory.spend_update_queue.size',
    'litellm.input.tokens.count',
    'litellm.llm.api.failed_requests.metric.count',
    'litellm.llm.api.latency.metric.bucket',
    'litellm.llm.api.latency.metric.count',
    'litellm.llm.api.latency.metric.sum',
    'litellm.llm.api.time_to_first_token.metric.bucket',
    'litellm.llm.api.time_to_first_token.metric.count',
    'litellm.llm.api.time_to_first_token.metric.sum',
    'litellm.output.tokens.count',
    'litellm.overhead_latency.metric.bucket',
    'litellm.overhead_latency.metric.count',
    'litellm.overhead_latency.metric.sum',
    'litellm.pod_lock_manager.size',
    'litellm.postgres.failed_requests.count',
    'litellm.postgres.latency.bucket',
    'litellm.postgres.latency.count',
    'litellm.postgres.latency.sum',
    'litellm.postgres.total_requests.count',
    'litellm.provider.remaining_budget.metric',
    'litellm.proxy.failed_requests.metric.count',
    'litellm.proxy.pre_call.failed_requests.count',
    'litellm.proxy.pre_call.latency.bucket',
    'litellm.proxy.pre_call.latency.count',
    'litellm.proxy.pre_call.latency.sum',
    'litellm.proxy.pre_call.total_requests.count',
    'litellm.proxy.total_requests.metric.count',
    'litellm.redis.daily_spend_update_queue.size',
    'litellm.redis.daily_tag_spend_update_queue.failed_requests.count',
    'litellm.redis.daily_tag_spend_update_queue.latency.bucket',
    'litellm.redis.daily_tag_spend_update_queue.latency.count',
    'litellm.redis.daily_tag_spend_update_queue.latency.sum',
    'litellm.redis.daily_tag_spend_update_queue.total_requests.count',
    'litellm.redis.daily_team_spend_update_queue.failed_requests.count',
    'litellm.redis.daily_team_spend_update_queue.latency.bucket',
    'litellm.redis.daily_team_spend_update_queue.latency.count',
    'litellm.redis.daily_team_spend_update_queue.latency.sum',
    'litellm.redis.daily_team_spend_update_queue.total_requests.count',
    'litellm.redis.failed_requests.count',
    'litellm.redis.latency.bucket',
    'litellm.redis.spend_update_queue.size',
    'litellm.redis.total_requests.count',
    'litellm.remaining.api_key.budget.metric',
    'litellm.remaining.api_key.requests_for_model',
    'litellm.remaining.api_key.tokens_for_model',
    'litellm.remaining.requests',
    'litellm.remaining.team_budget.metric',
    'litellm.remaining_tokens',
    'litellm.request.total_latency.metric.bucket',
    'litellm.request.total_latency.metric.count',
    'litellm.request.total_latency.metric.sum',
    'litellm.requests.metric.count',
    'litellm.reset_budget_job.failed_requests.count',
    'litellm.reset_budget_job.latency.bucket',
    'litellm.reset_budget_job.total_requests.count',
    'litellm.router.failed_requests.count',
    'litellm.router.latency.bucket',
    'litellm.router.latency.count',
    'litellm.router.latency.sum',
    'litellm.router.total_requests.count',
    'litellm.self.failed_requests.count',
    'litellm.self.latency.bucket',
    'litellm.self.latency.count',
    'litellm.self.latency.sum',
    'litellm.self.total_requests.count',
    'litellm.spend.metric.count',
    'litellm.team.budget.remaining_hours.metric',
    'litellm.team.max_budget.metric',
    'litellm.total.tokens.count',
    "litellm.process.uptime.seconds",
]

ENDPOINT_METRICS = [
    'litellm.endpoint.info',
    'litellm.endpoint.healthy_count',
    'litellm.endpoint.unhealthy_count',
]

RENAMED_METRICS_V1_75 = [
    'litellm.total.tokens.count',
    'litellm.input_tokens.metric.count',
    'litellm.output_tokens.metric.count',
]
