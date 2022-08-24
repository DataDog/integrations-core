from datadog_checks.base import AgentCheck

METRICS = {
    "uptime": AgentCheck.gauge,
    "asserts.msg": AgentCheck.rate,
    "asserts.regular": AgentCheck.rate,
    "asserts.rollovers": AgentCheck.rate,
    "asserts.user": AgentCheck.rate,
    "asserts.warning": AgentCheck.rate,
}

CASE_SENSITIVE_METRIC_NAME_SUFFIXES = {
    r'\.R\b': ".shared",
    r'\.r\b': ".intent_shared",
    r'\.W\b': ".exclusive",
    r'\.w\b': ".intent_exclusive",
}
