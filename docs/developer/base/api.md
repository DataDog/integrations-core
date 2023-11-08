# API

-----

::: datadog_checks.base.checks.base.AgentCheck
    options:
      heading_level: 3
      members:
        - gauge
        - count
        - monotonic_count
        - rate
        - histogram
        - historate
        - service_check
        - event
        - set_metadata
        - metadata_entrypoint
        - read_persistent_cache
        - write_persistent_cache
        - warning

## Stubs

::: datadog_checks.base.stubs.aggregator.AggregatorStub
    options:
      heading_level: 3
      members:
        - assert_metric
        - assert_metric_has_tag
        - assert_metric_has_tag_prefix
        - assert_service_check
        - assert_event
        - assert_histogram_bucket
        - assert_metrics_using_metadata
        - assert_all_metrics_covered
        - assert_no_duplicate_metrics
        - assert_no_duplicate_service_checks
        - assert_no_duplicate_all
        - all_metrics_asserted
        - reset

::: datadog_checks.base.stubs.datadog_agent.DatadogAgentStub
    options:
      heading_level: 3
      members:
        - assert_metadata
        - assert_metadata_count
        - reset
