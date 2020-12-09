{license_header}
from datadog_checks.dev.jmx import JVM_E2E_METRICS

METRICS = [
    # integration metrics
] + JVM_E2E_METRICS
