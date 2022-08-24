from datadog_checks.base import AgentCheck

METRICS = {
    "uptime": AgentCheck.gauge,
    "asserts.msg": AgentCheck.rate,
    "asserts.regular": AgentCheck.rate,
    "asserts.rollovers": AgentCheck.rate,
    "asserts.user": AgentCheck.rate,
    "asserts.warning": AgentCheck.rate,
    "backgroundFlushing.average_ms": AgentCheck.gauge,
    "backgroundFlushing.flushes": AgentCheck.rate,
    "backgroundFlushing.last_ms": AgentCheck.gauge,
    "backgroundFlushing.total_ms": AgentCheck.gauge,
}

CASE_SENSITIVE_METRIC_NAME_SUFFIXES = {
    r'\.R\b': ".shared",
    r'\.r\b': ".intent_shared",
    r'\.W\b': ".exclusive",
    r'\.w\b': ".intent_exclusive",
}
