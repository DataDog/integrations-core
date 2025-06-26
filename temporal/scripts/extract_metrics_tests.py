# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import unittest

from generate_metadata import extract_metric_defs


class TestExtractMetricDefs(unittest.TestCase):
    def test_basic_metric_extraction(self):
        go_code = '''
        var (
            ServiceRequests = NewCounterDef("service_requests")
            ServicePendingRequests = NewGaugeDef("service_pending_requests")
            ServiceLatency = NewTimerDef("service_latency")
            EventBlobSize = NewBytesHistogramDef("event_blob_size")
            StateTransitionCount = NewDimensionlessHistogramDef("state_transition_count")
        )
        '''
        expected = {
            "service_requests": "counter",
            "service_pending_requests": "gauge",
            "service_latency": "timer",
            "event_blob_size": "byteshistogram",
            "state_transition_count": "dimensionlesshistogram",
        }
        self.assertEqual(extract_metric_defs(go_code), expected)

    def test_empty_input(self):
        self.assertEqual(extract_metric_defs(""), {})

    def test_no_matches(self):
        go_code = '''
        var (
            regularVar = "some value"
            anotherVar = 42
        )
        '''
        self.assertEqual(extract_metric_defs(go_code), {})

    def test_case_sensitivity(self):
        go_code = '''
        var (
            metric1 = NewCounterDef("METRIC.ONE")
            metric2 = NewTimerDef("metric.two")
        )
        '''
        expected = {"metric.one": "counter", "metric.two": "timer"}
        self.assertEqual(extract_metric_defs(go_code), expected)

    def test_complex_definitions(self):
        go_code = '''
        var (
            workflowCounter = NewCounterDef("workflow.counter")
            taskTimer = NewTimerDef("task.timer")
            operationGauge = NewGaugeDef("operation.gauge")
            // Some comments
            customMetric = NewCustomDef("custom.metric")
            // More comments
            anotherMetric = NewHistogramDef("another.metric")
            NonRetryableTasks                      = NewCounterDef(
		"non_retryable_tasks",
		WithDescription("The number of non-retryable matching tasks which are dropped due to specific errors"))
        )
        '''
        expected = {
            "workflow.counter": "counter",
            "task.timer": "timer",
            "operation.gauge": "gauge",
            "custom.metric": "custom",
            "another.metric": "histogram",
            "non_retryable_tasks": "counter",
        }
        self.assertEqual(extract_metric_defs(go_code), expected)


if __name__ == '__main__':
    unittest.main()
