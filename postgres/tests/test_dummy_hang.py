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


def _dummy_work():
    """Dummy function to call repeatedly in spin-wait loop."""
    result = 0
    for i in range(1000):
        result += i * i
    return result


def _dummy_test(test_name, duration_seconds):
    """Helper function that prints every 10 seconds using spin-wait for the specified duration."""
    print(f"\n[{test_name}] Starting - will run for {duration_seconds} seconds")

    start_time = time.time()
    last_print_time = start_time

    while True:
        # Spin-wait by calling dummy function
        _dummy_work()

        current_time = time.time()
        elapsed = current_time - start_time

        # Check if we should print (every 10 seconds)
        if current_time - last_print_time >= 10:
            print(f"[{test_name}] Elapsed: {int(elapsed)}s / {duration_seconds}s")
            last_print_time = current_time

        # Check if we're done
        if elapsed >= duration_seconds:
            break

    print(f"[{test_name}] Completed")


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
