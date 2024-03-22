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

MOCKED_APPSET_CONTROLLER_INSTANCE = {'appset_controller_endpoint': 'http://appset_controller:8080'}

MOCKED_API_SERVER_INSTANCE = {'api_server_endpoint': 'http://api_server:8083'}

MOCKED_REPO_SERVER_INSTANCE = {'repo_server_endpoint': 'http://repo_server:8084'}

MOCKED_NOTIFICATIONS_CONTROLLER_INSTANCE = {'notifications_controller_endpoint': 'http://notifications_controller:9001'}

app_controller_ns, appset_controller_ns, api_server_ns, repo_server_ns, notifications_controller_ns = (
    "argocd.app_controller",
    "argocd.appset_controller",
    "argocd.api_server",
    "argocd.repo_server",
    "argocd.notifications_controller",
)

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
    'go.memstats.mspan.inuse_bytes',
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
    'redis.request.count',
    'app.k8s.request.count',
    'app.sync.count',
    'cluster.events.count',
    'kubectl.exec.count',
    'workqueue.adds.count',
    'workqueue.retries.count',
    'process.cpu.seconds.count',
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

appset_controller_counters = ['reconcile.errors.total', 'runtime.reconcile.total']

appset_controller_gauges = [
    'active.workers',
    'max.concurrent.reconciles',
]

appset_controller_histograms = [
    'reconcile.time_seconds.bucket',
    'reconcile.time_seconds.count',
    'reconcile.time_seconds.sum',
]

api_server_counters = [
    'redis.request.count',
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
    'redis.request.count',
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

notifications_controller_counters = [
    'notifications.deliveries.count',
    'notifications.trigger_eval.count',
]

NOT_EXPOSED_METRICS = [
    'argocd.app_controller.cluster.api.resource_objects',
    'argocd.app_controller.cluster.api.resources',
    'argocd.app_controller.cluster.cache.age.seconds',
    'argocd.app_controller.redis.request.duration',
    'argocd.appset_controller.reconcile.errors.total',
    'argocd.appset_controller.runtime.reconcile.total',
]

# Additional metrics that aren't exposed in the E2E environment
E2E_NOT_EXPOSED_METRICS = [
    'argocd.app_controller.app.k8s.request.count',
    'argocd.app_controller.app.sync.count',
    'argocd.app_controller.cluster.events.count',
    'argocd.app_controller.kubectl.exec.count',
    'argocd.app_controller.app.info',
    'argocd.app_controller.app.reconcile.bucket',
    'argocd.app_controller.app.reconcile.count',
    'argocd.app_controller.app.reconcile.sum',
    'argocd.app_controller.kubectl.exec.pending',
    'argocd.appset_controller.reconcile.time_seconds.bucket',
    'argocd.appset_controller.reconcile.time_seconds.count',
    'argocd.appset_controller.reconcile.time_seconds.sum',
    'argocd.api_server.redis.request.duration.bucket',
    'argocd.api_server.redis.request.duration.count',
    'argocd.api_server.redis.request.duration.sum',
    'argocd.api_server.redis.request.count',
    'argocd.app_controller.kubectl.exec.pending',
    'argocd.notifications_controller.notifications.deliveries.count',
    'argocd.notifications_controller.notifications.trigger_eval.count',
    'argocd.repo_server.repo.pending.request.total',
    'argocd.repo_server.git.request.count',
    'argocd.repo_server.git.request.duration.seconds.bucket',
    'argocd.repo_server.git.request.duration.seconds.count',
    'argocd.repo_server.git.request.duration.seconds.sum',
    'argocd.repo_server.redis.request.duration.seconds.bucket',
    'argocd.repo_server.redis.request.duration.seconds.count',
    'argocd.repo_server.redis.request.duration.seconds.sum',
    'argocd.repo_server.redis.request.count',
]

general = general_gauges + general_counters + general_summaries

app_controller = app_controller_counters + app_controller_gauges + app_controller_histograms + general
appset_controller = appset_controller_counters + appset_controller_gauges + appset_controller_histograms + general
api_server = api_server_counters + api_server_histograms + general
repo_server = repo_server_counters + repo_server_gauges + repo_server_histograms + general
notifications_controller = notifications_controller_counters + general


def namespace_formatter(metrics, namespace):
    formatted_metric = []
    for metric in metrics:
        formatted_metric.append(namespace + '.' + metric)
    return formatted_metric


APP_CONTROLLER_METRICS = namespace_formatter(app_controller, app_controller_ns)
APPSET_CONTROLLER_METRICS = namespace_formatter(appset_controller, appset_controller_ns)
API_SERVER_METRICS = namespace_formatter(api_server, api_server_ns)
REPO_SERVER_METRICS = namespace_formatter(repo_server, repo_server_ns)
NOTIFICATIONS_CONTROLLER_METRICS = namespace_formatter(notifications_controller, notifications_controller_ns)
