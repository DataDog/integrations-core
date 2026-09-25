# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""slurmrestd (REST) collection mode for the Slurm check.

Optional alternative to the CLI collectors: query the Slurm REST API (slurmrestd) over HTTP
with a JWT token (auth/jwt) instead of executing the Slurm CLI binaries. This lets the check
run without co-located Slurm binaries or munge/auth access -- for example as a cluster check
against a containerized Slurm deployment (SUNK/Slinky), including deployments that have NO
login node: the check talks to the slurmrestd service over the network from wherever it runs,
and the JWT is provided out-of-band (token/token_file), so no login pod is required.

slurmrestd is optional in Slurm and may be disabled. SlurmRestAPIClient.get never raises on
transport or API errors; it logs and returns None so the caller can emit a can_connect service
check and skip metrics for that run.

Metric names and tags mirror the CLI collectors so REST and CLI are schema-compatible.
"""

# slurmrestd /diag `statistics` key -> slurm.* metric name (matches the CLI sdiag metric names).
# Note: `schedule_cycle_total` is the scheduling-cycle COUNT (verified: total=340, sum=3255,
# mean=9), which matches the CLI "Total cycles:" value.
SDIAG_REST_METRIC_MAP = {
    'server_thread_count': 'sdiag.server_thread_count',
    'agent_queue_size': 'sdiag.agent_queue_size',
    'agent_count': 'sdiag.agent_count',
    'agent_thread_count': 'sdiag.agent_thread_count',
    'dbd_agent_queue_size': 'sdiag.dbd_agent_queue_size',
    'schedule_queue_length': 'sdiag.last_queue_length',
    'jobs_submitted': 'sdiag.jobs_submitted',
    'jobs_started': 'sdiag.jobs_started',
    'jobs_completed': 'sdiag.jobs_completed',
    'jobs_failed': 'sdiag.jobs_failed',
    'jobs_canceled': 'sdiag.jobs_canceled',
    'jobs_pending': 'sdiag.jobs_pending',
    'jobs_running': 'sdiag.jobs_running',
    'schedule_cycle_last': 'sdiag.last_cycle',
    'schedule_cycle_max': 'sdiag.max_cycle',
    'schedule_cycle_total': 'sdiag.total_cycles',
    'schedule_cycle_mean': 'sdiag.mean_cycle',
    'schedule_cycle_mean_depth': 'sdiag.mean_depth_cycle',
    'schedule_cycle_per_minute': 'sdiag.cycles_per_minute',
    # Backfill scheduler statistics.
    'bf_backfilled_jobs': 'sdiag.backfill.total_jobs_since_start',
    'bf_last_backfilled_jobs': 'sdiag.backfill.total_jobs_since_cycle_start',
    'bf_backfilled_het_jobs': 'sdiag.backfill.total_heterogeneous_components',
    'bf_cycle_counter': 'sdiag.backfill.total_cycles',
    'bf_cycle_last': 'sdiag.backfill.last_cycle',
    'bf_cycle_max': 'sdiag.backfill.max_cycle',
    'bf_cycle_mean': 'sdiag.backfill.mean_cycle',
    'bf_last_depth': 'sdiag.backfill.last_depth_cycle',
    'bf_last_depth_try': 'sdiag.backfill.last_depth_try_schedule',
    'bf_depth_mean': 'sdiag.backfill.depth_mean',
    'bf_depth_mean_try': 'sdiag.backfill.depth_mean_try_depth',
    'bf_queue_len': 'sdiag.backfill.last_queue_length',
    'bf_queue_len_mean': 'sdiag.backfill.queue_length_mean',
    'bf_table_size': 'sdiag.backfill.last_table_size',
    'bf_table_size_mean': 'sdiag.backfill.mean_table_size',
}


def unwrap_number(value):
    """slurmrestd wraps some numeric fields as {"set": bool, "infinite": bool, "number": N}."""
    if isinstance(value, dict):
        if not value.get('set', True) or value.get('infinite'):
            return None
        return value.get('number')
    return value


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def gpu_count_from_gres(gres: str | None) -> tuple[str | None, int | None]:
    """Parse a GRES string into (gpu_type, gpu_count).

    Handles the shapes slurmrestd emits for node ``gres``/``gres_used``: ``"gpu:1"`` (no type),
    ``"gpu:tesla_t4:4"`` (with type), and a ``(IDX:...)`` allocation suffix on the used string
    (``"gpu:tesla_t4:2(IDX:0-1)"``). Comma-separated multi-GRES uses the first gpu entry. Returns
    (None, None) when there is no gpu GRES or the count is unparseable.
    """
    if not gres:
        return None, None
    for segment in gres.split(','):
        head = segment.split('(')[0].strip()
        parts = head.split(':')
        if len(parts) < 2 or parts[0] != 'gpu':
            continue
        gpu_type = parts[1] if len(parts) >= 3 else None
        try:
            return gpu_type, int(parts[-1])
        except ValueError:
            return None, None
    return None, None


class SlurmRestAPIClient:
    """Thin slurmrestd HTTP client. Never raises on transport/API errors -- returns None.

    `token` is set by the caller once per check run (so a rotated token file is read at most
    once per run rather than once per request). `user` is optional and only needed behind an
    authenticating proxy that reuses one privileged token for multiple users -- a direct
    per-user JWT already identifies the user via its own claims, per
    https://slurm.schedmd.com/jwt.html.
    """

    def __init__(self, http, base_url, openapi_version, log):
        self.http = http
        self.base_url = base_url.rstrip('/')
        self.openapi_version = openapi_version
        self.log = log
        self.token = None
        self.user = None

    def _headers(self):
        headers = {}
        if self.token:
            headers['X-SLURM-USER-TOKEN'] = self.token
        if self.user:
            headers['X-SLURM-USER-NAME'] = self.user
        return headers

    def get(self, resource):
        """GET /slurm/<version>/<resource>. Returns the parsed dict, or None on any failure."""
        url = f'{self.base_url}/slurm/{self.openapi_version}/{resource}'
        try:
            response = self.http.get(url, extra_headers=self._headers())
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            self.log.error("slurmrestd request to %s failed: %s", url, e)
            return None
        if not isinstance(payload, dict):
            self.log.error("slurmrestd returned an unexpected (non-object) payload for %s", resource)
            return None
        errors = payload.get('errors') or []
        if errors:
            self.log.error(
                "slurmrestd returned errors for %s (is slurmrestd enabled and the token valid?): %s",
                resource,
                errors,
            )
            return None
        return payload


def iter_sdiag_metrics(payload):
    """Yield (metric_name, value, tags) for scheduler diagnostics from a /diag payload."""
    statistics = (payload or {}).get('statistics', {})
    for key, metric in SDIAG_REST_METRIC_MAP.items():
        value = unwrap_number(statistics.get(key))
        if is_number(value):
            yield metric, value, []


def iter_partition_metrics(payload):
    """Yield (metric_name, value, tags) per partition from a /partitions payload.

    Mirrors the CLI level-1 (default) collection, which emits partition-scoped metrics. Known
    gap: the CLI path also emits a per-partition node-state breakdown
    (partition.node.allocated/idle/other/total, from `sinfo`'s AIOT columns); REST does not,
    since that requires a per-partition node-state count not present in the /partitions payload.
    """
    for partition in (payload or {}).get('partitions', []):
        name = (partition.get('name') or '').strip()
        if not name:
            continue
        tags = [
            f'slurm_partition_name:{name}',
            f'slurm_cluster_name:{partition.get("cluster") or "null"}',
        ]
        nodes = partition.get('nodes') if isinstance(partition.get('nodes'), dict) else {}
        node_total = unwrap_number(nodes.get('total'))
        if is_number(node_total):
            yield 'partition.nodes.count', node_total, tags
        info_tags = list(tags)
        node_list = nodes.get('configured')
        if node_list:
            info_tags.append(f'slurm_partition_node_list:{node_list}')
        yield 'partition.info', 1, info_tags


def iter_node_metrics(payload, collect_gpu=False):
    """Yield (metric_name, value, tags) per node from a /nodes payload.

    Emits once per (node, partition) to mirror the CLI `sinfo -N` (one row per node per
    partition) so `slurm_partition_name` is single-valued. Descriptive tags (state, features)
    are attached to `node.info` only -- matching the CLI, where the scalar node metrics do not
    carry the state tag. When collect_gpu is set, node.gpu_total/gpu_used are emitted from the
    node's gres/gres_used strings, carrying the CLI's slurm_node_gpu_type tag.
    """
    for node in (payload or {}).get('nodes', []):
        name = node.get('name')
        if not name:
            continue
        gpu_metrics = {}
        gpu_tag = []
        if collect_gpu:
            gpu_type, gpu_total = gpu_count_from_gres(node.get('gres'))
            _, gpu_used = gpu_count_from_gres(node.get('gres_used'))
            gpu_metrics = {'node.gpu_total': gpu_total, 'node.gpu_used': gpu_used}
            gpu_tag = [f'slurm_node_gpu_type:{gpu_type or "null"}']
        cpu_load = unwrap_number(node.get('cpu_load'))
        # Every numeric field is routed through unwrap_number: slurmrestd's data_parser wraps
        # some integer fields as {"set","infinite","number"} depending on OpenAPI/build version,
        # and unwrap_number is a no-op on plain numbers, so this is safe regardless of whether a
        # given field happens to be wrapped on a particular cluster.
        scalar_metrics = {
            'node.cpu.total': unwrap_number(node.get('cpus')),
            'node.cpu.allocated': unwrap_number(node.get('alloc_cpus')),
            'node.cpu.idle': unwrap_number(node.get('alloc_idle_cpus')),
            # slurmrestd reports cpu_load scaled x100 (e.g. 305 == load 3.05); match the CLI value.
            'node.cpu_load': cpu_load / 100.0 if is_number(cpu_load) else None,
            'node.memory': unwrap_number(node.get('real_memory')),
            'node.alloc_mem': unwrap_number(node.get('alloc_memory')),
            'node.free_mem': unwrap_number(node.get('free_mem')),
            'node.tmp_disk': unwrap_number(node.get('temporary_disk')),
        }
        identity_tags = [
            f'slurm_node_name:{name}',
            # Note: the /nodes payload keys this `cluster_name`, while /partitions keys the same
            # concept `cluster` -- different slurmrestd schema keys for the same field, not a bug.
            f'slurm_cluster_name:{node.get("cluster_name") or "null"}',
        ]
        states = [s.lower() for s in (node.get('state') or [])]
        features = ','.join(node.get('active_features') or [])
        partition_tags = [f'slurm_partition_name:{p}' for p in (node.get('partitions') or [])] or [None]

        for partition_tag in partition_tags:
            tags = identity_tags + ([partition_tag] if partition_tag else [])
            for metric, value in scalar_metrics.items():
                if is_number(value):
                    yield metric, value, tags
            for metric, value in gpu_metrics.items():
                if is_number(value):
                    yield metric, value, tags + gpu_tag
            info_tags = tags + [
                'slurm_node_state:' + (','.join(states) if states else 'unknown'),
                f'slurm_node_active_features:{features}',
            ]
            yield 'node.info', 1, info_tags


def iter_partition_gpu_metrics(payload):
    """Yield (metric_name, value, tags) for per-partition GPU totals, aggregated from a /nodes
    payload. slurmrestd's /partitions payload carries no GPU field, so partition.gpu_total and
    partition.gpu_used are summed from each node's gres/gres_used over the node's partition
    membership. gpu_type is intentionally omitted (unlike the per-node metric): a partition can
    span nodes with differing GPU types, so a single type tag on the aggregate would be misleading.
    """
    totals = {}
    for node in (payload or {}).get('nodes', []):
        _, node_total = gpu_count_from_gres(node.get('gres'))
        _, node_used = gpu_count_from_gres(node.get('gres_used'))
        if node_total is None and node_used is None:
            continue
        cluster = node.get('cluster_name') or 'null'
        for partition in node.get('partitions') or []:
            agg = totals.setdefault(partition, {'total': 0, 'used': 0, 'seen': False, 'cluster': cluster})
            if node_total is not None:
                agg['total'] += node_total
                agg['seen'] = True
            if node_used is not None:
                agg['used'] += node_used
                agg['seen'] = True
    for partition, agg in totals.items():
        if not agg['seen']:
            continue
        tags = [f'slurm_partition_name:{partition}', f'slurm_cluster_name:{agg["cluster"]}']
        yield 'partition.gpu_total', agg['total'], tags
        yield 'partition.gpu_used', agg['used'], tags
