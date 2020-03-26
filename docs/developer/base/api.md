# API

-----

::: datadog_checks.base.AgentCheck
    rendering:
      heading_level: 3
    selection:
      members:
        - __init__
        - gauge
        - count
        - monotonic_count
        - rate
        - histogram
        - historate
        - service_check
        - event

## Stubs

::: datadog_checks.base.stubs.aggregator.AggregatorStub
    rendering:
      heading_level: 3
    selection:
      members:
        - assert_metric
        - assert_metric_has_tag
        - assert_metric_has_tag_prefix
        - assert_service_check
        - assert_event
        - assert_all_metrics_covered
        - assert_no_duplicate_metrics
        - assert_no_duplicate_service_checks
        - assert_no_duplicate_all reset

::: datadog_checks.base.stubs.datadog_agent.DatadogAgentStub
    rendering:
      heading_level: 3
