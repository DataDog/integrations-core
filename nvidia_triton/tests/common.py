import os

from datadog_checks.dev import get_here

HERE = get_here()
def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


INSTANCE_MOCK = {
    'openmetrics_endpoint': 'http://triton:8002/metrics',
    'weaviate_api_endpoint': 'http://triton:8000',
    'tags': ['env:test'],
}

METRICS_MOCK = {
    'nv.cache.insertion.duration',
    'nv.cache.lookup.duration',
    'nv.cache.num.entries',
    'nv.cache.num.evictions',
    'nv.cache.num.hits',
    'nv.cache.num.lookups',
    'nv.cache.num.misses',
    'nv.cache.util',
    'nv.cpu.memory.total_bytes',
    'nv.cpu.memory.used_bytes',
    'nv.cpu.utilization',
    'nv.energy.consumption',
    'nv.gpu.memory.total_bytes',
    'nv.gpu.memory.used_bytes',
    'nv.gpu.power.limit',
    'nv.gpu.power.usage',
    'nv.gpu.utilization',
    'nv.inference.compute.infer.duration_us',
    'nv.inference.compute.infer.summary_us.sum',
    'nv.inference.compute.infer.summary_us.count',
    'nv.inference.compute.infer.summary_us.quantile',
    'nv.inference.compute.input.duration_us',
    'nv.inference.compute.input.summary_us.sum',
    'nv.inference.compute.input.summary_us.count',
    'nv.inference.compute.input.summary_us.quantile',
    'nv.inference.compute.output.duration_us',
    'nv.inference.compute.output.summary_us.sum',
    'nv.inference.compute.output.summary_us.count',
    'nv.inference.compute.output.summary_us.quantile',
    'nv.inference.count',
    'nv.inference.exec.count',
    'nv.inference.pending.request.count',
    'nv.inference.queue.duration_us',
    'nv.inference.queue.summary_us.sum',
    'nv.inference.queue.summary_us.count',
    'nv.inference.queue.summary_us.quantile',
    'nv.inference.request.duration_us',
    'nv.inference.request.summary_us.sum',
    'nv.inference.request.summary_us.count',
    'nv.inference.request.summary_us.quantile',
    'nv.inference.request_failure',
    'nv.inference.request_success',
}
