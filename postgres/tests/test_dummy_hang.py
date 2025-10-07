# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Dummy tests to reproduce hang in test framework or tracing.
These tests do not set up any environment or run actual postgres integration.
They just print a line every 10 seconds and use spin-wait instead of sleep.
Total duration: ~10 minutes across all tests running sequentially.
"""

import time

import pytest
from ddtrace import tracer


@tracer.wrap(service="dummy-tests", resource="dummy_work")
def _dummy_work():
    """Dummy function to call repeatedly in spin-wait loop."""
    result = 0
    for i in range(1000):
        result += i * i
    return result


def _dummy_test(test_name, duration_seconds):
    """Helper function that prints every 10 seconds using spin-wait for the specified duration."""
    with tracer.trace("dummy_test", service="dummy-tests", resource=test_name) as test_span:
        test_span.set_tag("test.name", test_name)
        test_span.set_tag("test.duration", duration_seconds)

        print(f"\n[{test_name}] Starting - will run for {duration_seconds} seconds")
        print(f"[TRACE] Created span: {test_span.name} (trace_id={test_span.trace_id}, span_id={test_span.span_id})")

        start_time = time.time()
        last_print_time = start_time
        iteration_count = 0

        with tracer.trace("spin_wait_loop", service="dummy-tests", resource=f"{test_name}_loop") as loop_span:
            print(f"[TRACE] Started loop span: {loop_span.name} (span_id={loop_span.span_id})")

            while True:
                # Spin-wait by calling dummy function
                _dummy_work()
                iteration_count += 1

                current_time = time.time()
                elapsed = current_time - start_time

                # Check if we should print (every 10 seconds)
                if current_time - last_print_time >= 10:
                    with tracer.trace("progress_print", service="dummy-tests") as print_span:
                        print_span.set_tag("elapsed", int(elapsed))
                        print_span.set_tag("total_duration", duration_seconds)
                        print(f"[{test_name}] Elapsed: {int(elapsed)}s / {duration_seconds}s")
                        print(f"[TRACE] Progress span created (iterations so far: {iteration_count})")
                    last_print_time = current_time

                # Check if we're done
                if elapsed >= duration_seconds:
                    break

            loop_span.set_tag("total_iterations", iteration_count)
            print(f"[TRACE] Loop span completed with {iteration_count} iterations")

        print(f"[{test_name}] Completed")
        print(f"[TRACE] Test span completed: {test_span.name}")


# 10 tests with durations that add up to ~600 seconds (10 minutes)
# Each test runs for 60 seconds
@pytest.mark.integration
def test_dummy_01():
    _dummy_test("test_dummy_01", 60)


@pytest.mark.integration
def test_dummy_02():
    _dummy_test("test_dummy_02", 60)


@pytest.mark.integration
def test_dummy_03():
    _dummy_test("test_dummy_03", 60)


@pytest.mark.integration
def test_dummy_04():
    _dummy_test("test_dummy_04", 60)


@pytest.mark.integration
def test_dummy_05():
    _dummy_test("test_dummy_05", 60)


@pytest.mark.integration
def test_dummy_06():
    _dummy_test("test_dummy_06", 60)


@pytest.mark.integration
def test_dummy_07():
    _dummy_test("test_dummy_07", 60)


@pytest.mark.integration
def test_dummy_08():
    _dummy_test("test_dummy_08", 60)


@pytest.mark.integration
def test_dummy_09():
    _dummy_test("test_dummy_09", 60)


@pytest.mark.integration
def test_dummy_10():
    _dummy_test("test_dummy_10", 60)
