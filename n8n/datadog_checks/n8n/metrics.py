# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Metrics emitted by n8n's /metrics endpoint, verified live against n8n@1.118.1
# and n8n@2.19.5.
#
# The OpenMetrics base check strips `_total` from counter names before lookup
# and appends `.count` on submission, so counter keys here are written without
# the `_total` suffix (e.g. `cache_hits_total` -> key `cache_hits`).
#
# Many counters are dynamically registered from EventBus events (event
# `n8n.<a>.<b>.<c>` becomes counter `<a>_<b>_<c>_total`) and only appear once
# the corresponding event fires at runtime. In queue mode, worker processes
# emit `node_started_total`, `node_finished_total`, `queue_job_dequeued_total`,
# `queue_job_stalled_total`, and `runner_task_requested_total`.
#
# Several families were introduced in n8n 2.x (see the README "Version-specific
# metrics" section). The `workflow_statistics_*` and SSO/embed token-exchange
# families require additional flags (`N8N_METRICS_INCLUDE_WORKFLOW_STATISTICS`,
# token-exchange counters always register but only emit on auth events).
# Event-bus events whose generated counter name contains a hyphen are silently rejected
# by n8n's own ``prom-client.validateMetricName`` check (see ``prometheus-metrics.service.ts``).
# These events are emitted on the bus and reach n8n's event-log file but never register a
# Prometheus counter on /metrics, so they are intentionally absent from ``METRIC_MAP``:
#   audit.2fa-enforcement.{enabled,disabled}
#   audit.cluster.{hostid-clash,split-brain,version-mismatch}.{detected,resolved}
#   audit.cluster.{instance-joined,instance-left}
#   audit.external-secrets.connection.{created,deleted,reloaded,tested,updated}
#   audit.external-secrets.provider.{reloaded,settings.saved}
#   audit.personal-{publishing,sharing}-restricted.{enabled,disabled}
#   audit.role-mapping.rule.{created,updated,deleted}
#   audit.role-mapping.{roles-resolved,rules.bulk-deleted}
#   audit.token-exchange.{succeeded,failed,identity-linked,user-provisioned,role-updated,embed-login,embed-login-failed}
#   execution.started-during-bootup
# To collect these signals, tail n8n's event-log files via the ``logs`` block instead of /metrics.
METRIC_MAP = {
    'active_workflow_count': 'active.workflow.count',
    'ai_document_processed': 'ai.document.processed',
    'ai_embeddings_embedded_document': 'ai.embeddings.embedded.document',
    'ai_embeddings_embedded_query': 'ai.embeddings.embedded.query',
    'ai_llm_error': 'ai.llm.error',
    'ai_llm_generated': 'ai.llm.generated',
    'ai_memory_added_message': 'ai.memory.added.message',
    'ai_memory_get_messages': 'ai.memory.get.messages',
    'ai_output_parser_parsed': 'ai.output.parser.parsed',
    'ai_retriever_get_relevant_documents': 'ai.retriever.get.relevant.documents',
    'ai_text_splitter_split': 'ai.text.splitter.split',
    'ai_tool_called': 'ai.tool.called',
    'ai_vector_store_populated': 'ai.vector.store.populated',
    'ai_vector_store_searched': 'ai.vector.store.searched',
    'ai_vector_store_updated': 'ai.vector.store.updated',
    'audit_execution_data_reveal_failure': 'audit.execution.data.reveal_failure',
    'audit_execution_data_revealed': 'audit.execution.data.revealed',
    'audit_package_deleted': 'audit.package.deleted',
    'audit_package_installed': 'audit.package.installed',
    'audit_package_updated': 'audit.package.updated',
    'audit_user_api_created': 'audit.user.api.created',
    'audit_user_api_deleted': 'audit.user.api.deleted',
    'audit_user_credentials_created': 'audit.user.credentials.created',
    'audit_user_credentials_deleted': 'audit.user.credentials.deleted',
    'audit_user_credentials_shared': 'audit.user.credentials.shared',
    'audit_user_credentials_updated': 'audit.user.credentials.updated',
    'audit_user_deleted': 'audit.user.deleted',
    'audit_user_email_failed': 'audit.user.email.failed',
    'audit_user_execution_deleted': 'audit.user.execution.deleted',
    'audit_user_invitation_accepted': 'audit.user.invitation.accepted',
    'audit_user_invited': 'audit.user.invited',
    'audit_user_login_failed': 'audit.user.login.failed',
    'audit_user_login_success': 'audit.user.login.success',
    'audit_user_mfa_disabled': 'audit.user.mfa.disabled',
    'audit_user_mfa_enabled': 'audit.user.mfa.enabled',
    'audit_user_reinvited': 'audit.user.reinvited',
    'audit_user_reset': 'audit.user.reset',
    'audit_user_reset_requested': 'audit.user.reset.requested',
    'audit_user_signedup': 'audit.user.signedup',
    'audit_user_updated': 'audit.user.updated',
    'audit_variable_created': 'audit.variable.created',
    'audit_variable_deleted': 'audit.variable.deleted',
    'audit_variable_updated': 'audit.variable.updated',
    'audit_workflow_activated': 'audit.workflow.activated',  # n8n 2.x+
    'audit_workflow_archived': 'audit.workflow.archived',
    'audit_workflow_created': 'audit.workflow.created',
    'audit_workflow_deactivated': 'audit.workflow.deactivated',  # n8n 2.x+
    'audit_workflow_deleted': 'audit.workflow.deleted',
    'audit_workflow_executed': 'audit.workflow.executed',  # n8n 2.x+
    'audit_workflow_resumed': 'audit.workflow.resumed',  # n8n 2.x+
    'audit_workflow_unarchived': 'audit.workflow.unarchived',
    'audit_workflow_updated': 'audit.workflow.updated',
    'audit_workflow_version_updated': 'audit.workflow.version.updated',  # n8n 2.x+
    'audit_workflow_waiting': 'audit.workflow.waiting',  # n8n 2.x+
    'cache_hits': 'cache.hits',
    'cache_misses': 'cache.misses',
    'cache_updates': 'cache.updates',
    'credentials': 'credentials.total',  # n8n 2.x+, requires N8N_METRICS_INCLUDE_WORKFLOW_STATISTICS
    'embed_login_failures': 'embed.login.failures',  # n8n 2.x+
    'embed_login_requests': 'embed.login.requests',  # n8n 2.x+
    'enabled_users': 'enabled.users',  # n8n 2.x+, requires N8N_METRICS_INCLUDE_WORKFLOW_STATISTICS
    'execution_throttled': 'execution.throttled',
    'expression_code_cache_eviction': 'expression.code.cache.eviction',
    'expression_code_cache_hit': 'expression.code.cache.hit',
    'expression_code_cache_miss': 'expression.code.cache.miss',
    'expression_code_cache_size': 'expression.code.cache.size',
    'expression_evaluation_duration_seconds': 'expression.evaluation.duration.seconds',
    'expression_pool_acquired': 'expression.pool.acquired',
    'expression_pool_replenish_failed': 'expression.pool.replenish.failed',
    'expression_pool_scaled_to_zero': 'expression.pool.scaled.to.zero',
    'expression_pool_scaled_up': 'expression.pool.scaled.up',
    'http_request_duration_seconds': 'http.request.duration.seconds',
    'instance_role_leader': 'instance.role.leader',
    'last_activity': {'name': 'last.activity', 'type': 'time_elapsed'},
    'manual_executions': 'manual.executions',  # n8n 2.x+, requires N8N_METRICS_INCLUDE_WORKFLOW_STATISTICS
    'node_finished': 'node.finished',
    'node_started': 'node.started',
    'nodejs_active_handles': 'nodejs.active.handles',
    'nodejs_active_handles_total': 'nodejs.active.handles.total',
    'nodejs_active_requests': 'nodejs.active.requests',
    'nodejs_active_requests_total': 'nodejs.active.requests.total',
    'nodejs_active_resources': 'nodejs.active.resources',
    'nodejs_active_resources_total': 'nodejs.active.resources.total',
    'nodejs_eventloop_lag_max_seconds': 'nodejs.eventloop.lag.max.seconds',
    'nodejs_eventloop_lag_mean_seconds': 'nodejs.eventloop.lag.mean.seconds',
    'nodejs_eventloop_lag_min_seconds': 'nodejs.eventloop.lag.min.seconds',
    'nodejs_eventloop_lag_p50_seconds': 'nodejs.eventloop.lag.p50.seconds',
    'nodejs_eventloop_lag_p90_seconds': 'nodejs.eventloop.lag.p90.seconds',
    'nodejs_eventloop_lag_p99_seconds': 'nodejs.eventloop.lag.p99.seconds',
    'nodejs_eventloop_lag_seconds': 'nodejs.eventloop.lag.seconds',
    'nodejs_eventloop_lag_stddev_seconds': 'nodejs.eventloop.lag.stddev.seconds',
    'nodejs_external_memory_bytes': 'nodejs.external.memory.bytes',
    'nodejs_gc_duration_seconds': 'nodejs.gc.duration.seconds',
    'nodejs_heap_size_total_bytes': 'nodejs.heap.size.total.bytes',
    'nodejs_heap_size_used_bytes': 'nodejs.heap.size.used.bytes',
    'nodejs_heap_space_size_available_bytes': 'nodejs.heap.space.size.available.bytes',
    'nodejs_heap_space_size_total_bytes': 'nodejs.heap.space.size.total.bytes',
    'nodejs_heap_space_size_used_bytes': 'nodejs.heap.space.size.used.bytes',
    'nodejs_version_info': {'type': 'metadata', 'label': 'version', 'name': 'nodejs.version'},
    'process_cpu_seconds': 'process.cpu.seconds',
    'process_cpu_system_seconds': 'process.cpu.system.seconds',
    'process_cpu_user_seconds': 'process.cpu.user.seconds',
    'process_heap_bytes': 'process.heap.bytes',
    'process_max_fds': 'process.max.fds',
    'process_open_fds': 'process.open.fds',
    'process_pss_bytes': 'process.pss.bytes',  # n8n 2.x+
    'process_resident_memory_bytes': 'process.resident.memory.bytes',
    'process_start_time_seconds': {'name': 'process.uptime.seconds', 'type': 'time_elapsed'},
    'process_virtual_memory_bytes': 'process.virtual.memory.bytes',
    'production_executions': 'production.executions',  # n8n 2.x+, requires N8N_METRICS_INCLUDE_WORKFLOW_STATISTICS
    'production_root_executions': 'production.root.executions',  # n8n 2.x+, requires flag
    'queue_job_completed': 'queue.job.completed',
    'queue_job_dequeued': 'queue.job.dequeued',
    'queue_job_enqueued': 'queue.job.enqueued',
    'queue_job_failed': 'queue.job.failed',
    'queue_job_stalled': 'queue.job.stalled',
    'runner_response_received': 'runner.response.received',
    'runner_task_requested': 'runner.task.requested',
    'scaling_mode_queue_jobs_active': 'scaling.mode.queue.jobs.active',
    'scaling_mode_queue_jobs_completed': 'scaling.mode.queue.jobs.completed',
    'scaling_mode_queue_jobs_failed': 'scaling.mode.queue.jobs.failed',
    'scaling_mode_queue_jobs_waiting': 'scaling.mode.queue.jobs.waiting',
    'token_exchange_failures': 'token.exchange.failures',  # n8n 2.x+
    'token_exchange_identity_linked': 'token.exchange.identity.linked',  # n8n 2.x+
    'token_exchange_jit_provisioning': 'token.exchange.jit.provisioning',  # n8n 2.x+
    'token_exchange_requests': 'token.exchange.requests',  # n8n 2.x+
    'users': 'users.total',  # n8n 2.x+, requires N8N_METRICS_INCLUDE_WORKFLOW_STATISTICS
    'version_info': {'type': 'metadata', 'label': 'version', 'name': 'version'},
    'workflow_cancelled': 'workflow.cancelled',
    'workflow_execution_duration_seconds': 'workflow.execution.duration.seconds',  # n8n 2.x+
    'workflow_failed': 'workflow.failed',
    'workflow_started': 'workflow.started',
    'workflow_success': 'workflow.success',
    'workflows': 'workflows.total',  # n8n 2.x+, requires N8N_METRICS_INCLUDE_WORKFLOW_STATISTICS
}

RENAME_LABELS_MAP = {
    'name': 'n8n_name',
    'namespace': 'n8n_namespace',
    'version': 'n8n_version',
}
