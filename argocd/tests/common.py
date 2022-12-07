# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

MOCKED_APP_CONTROLLER_INSTANCE = {'app_controller_endpoint': 'http://app_controller:8082'}

MOCKED_APP_CONTROLLER_WITH_OTHER_PARAMS = {
    'app_controller_endpoint': 'http://app_controller:8082',
    'empty_default_hostname': True,
    'enable_health_service_check': True,
    'collect_histogram_buckets': True,
}

MOCKED_API_SERVER_INSTANCE = {'api_server_endpoint': 'http://api_server:8083'}

MOCKED_REPO_SERVER_INSTANCE = {'repo_server_endpoint': 'http://repo_server:8084'}

EMPTY_INSTANCE = {''}

app_controller_ns, api_server_ns, repo_server_ns = ["argocd.app_controller", "argocd.api_server", "argocd.repo_server"]

general_gauges = [
    'go.goroutines',
    'go.memstats.alloc_bytes',
    'go.memstats.buck_hash.sys_bytes',
    'go.memstats.gc.cpu_fraction',
    'go.memstats.gc.sys_bytes',
    'go.memstats.heap.alloc_bytes',
    'go.memstats.heap.idle_bytes',
    'go.memstats.heap.inuse_bytes',
    'go.memstats.heap.objects',
    'go.memstats.heap.released_bytes',
    'go.memstats.heap.sys_bytes',
    'go.memstats.last_gc_time.seconds',
    'go.memstats.mcache.inuse_bytes',
    'go.memstats.mcache.sys_bytes',
    'go.memstats.mspan.inuse_use',
    'go.memstats.mspan.sys_bytes',
    'go.memstats.next.gc_bytes',
    'go.memstats.other.sys_bytes',
    'go.memstats.stack.inuse_bytes',
    'go.memstats.stack.sys_bytes',
    'go.memstats.sys_bytes',
    'go.threads',
    'process.max_fds',
    'process.open_fds',
    'process.resident_memory.bytes',
    'process.start_time.seconds',
    'process.virtual_memory.bytes',
    'process.virtual_memory.max_bytes',
]

general_counters = [
    'redis.request.count',
    'go.memstats.frees.count',
    'go.memstats.lookups.count',
    'go.memstats.mallocs.count',
    'process.cpu.seconds.count',
]

general_summaries = [
    'go.gc.duration.seconds.count',
    'go.gc.duration.seconds.quantile',
    'go.gc.duration.seconds.sum',
]

app_controller_counters = [
    'app.k8s.request.count',
    'app.sync.count',
    'cluster.events.count',
    'kubectl.exec.count',
    'workqueue.adds.count',
    'workqueue.retries.count',
]

app_controller_gauges = [
    'app.info',
    'cluster.api.resource_objects',
    'cluster.api.resources',
    'cluster.cache.age.seconds',
    'kubectl.exec.pending',
    'workqueue.depth',
    'workqueue.longest.running_processor.seconds',
    'workqueue.unfinished_work.seconds',
]

app_controller_histograms = [
    'app.reconcile.bucket',
    'app.reconcile.count',
    'app.reconcile.sum',
    'workqueue.queue.duration.seconds.bucket',
    'workqueue.queue.duration.seconds.count',
    'workqueue.queue.duration.seconds.sum',
    'workqueue.work.duration.seconds.bucket',
    'workqueue.work.duration.seconds.count',
    'workqueue.work.duration.seconds.sum',
    'redis.request.duration.bucket',
    'redis.request.duration.count',
    'redis.request.duration.sum',
]

api_server_counters = [
    'grpc.server.handled.count',
    'grpc.server.msg.sent.count',
    'grpc.server.msg.received.count',
    'grpc.server.started.count',
]

api_server_histograms = [
    'redis.request.duration.bucket',
    'redis.request.duration.count',
    'redis.request.duration.sum',
]

repo_server_gauges = [
    'repo.pending.request.total',
]

repo_server_counters = [
    'git.request.count',
]

repo_server_histograms = [
    'git.request.duration.seconds.bucket',
    'git.request.duration.seconds.count',
    'git.request.duration.seconds.sum',
    'redis.request.duration.seconds.bucket',
    'redis.request.duration.seconds.count',
    'redis.request.duration.seconds.sum',
]

NOT_EXPOSED_METRICS = [
    'argocd.api_server.redis.request.duration.bucket',
    'argocd.api_server.redis.request.duration.count',
    'argocd.api_server.redis.request.duration.sum',
    'argocd.api_server.redis.request.count',
    'argocd.app_controller.cluster.api.resource_objects',
    'argocd.app_controller.cluster.api.resources',
    'argocd.app_controller.cluster.cache.age.seconds',
    'argocd.app_controller.kubectl.exec.pending',
    'argocd.app_controller.redis.request.duration',
    'argocd.repo_server.redis.request.count',
    'argocd.repo_server.git.request.count',
    'argocd.repo_server.git.request.duration.seconds.bucket',
    'argocd.repo_server.git.request.duration.seconds.count',
    'argocd.repo_server.git.request.duration.seconds.sum',
    'argocd.repo_server.redis.request.duration.seconds.bucket',
    'argocd.repo_server.redis.request.duration.seconds.count',
    'argocd.repo_server.redis.request.duration.seconds.sum',
]

# Additional metrics that aren't exposed in the E2E environment
E2E_NOT_EXPOSED_METRICS = [
    'argocd.app_controller.app.k8s.request.count',
    'argocd.app_controller.process.cpu.seconds.count',
    'argocd.app_controller.app.sync.count',
    'argocd.app_controller.cluster.events.count',
    'argocd.app_controller.kubectl.exec.count',
    'argocd.app_controller.app.info',
    'argocd.app_controller.app.reconcile.bucket',
    'argocd.app_controller.app.reconcile.count',
    'argocd.app_controller.app.reconcile.sum',
    'argocd.repo_server.repo.pending.request.total',
]

general = general_gauges + general_counters + general_summaries

app_controller = app_controller_counters + app_controller_gauges + app_controller_histograms + general
api_server = api_server_counters + api_server_histograms + general
repo_server = repo_server_counters + repo_server_gauges + repo_server_histograms + general


def namespace_formatter(metrics, namespace):
    formatted_metric = []
    for metric in metrics:
        formatted_metric.append(namespace + '.' + metric)
    return formatted_metric


APP_CONTROLLER_METRICS = namespace_formatter(app_controller, app_controller_ns)
API_SERVER_METRICS = namespace_formatter(api_server, api_server_ns)
REPO_SERVER_METRICS = namespace_formatter(repo_server, repo_server_ns)
