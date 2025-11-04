#!/usr/bin/env python3
"""
Test script to verify ClickHouse query samples are being collected correctly.
Run this inside the datadog-agent container.
"""

import sys
import time
import subprocess
import json


def run_command(cmd):
    """Execute a shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


def test_clickhouse_query_log():
    """Test if ClickHouse has query log data."""
    print("=" * 60)
    print("TEST 1: Checking ClickHouse query_log table")
    print("=" * 60)

    query = """
    SELECT count(*) as query_count
    FROM system.query_log
    WHERE event_time > now() - INTERVAL 60 SECOND
    """

    cmd = f"clickhouse-client --host clickhouse-primary --port 9000 --user datadog --password datadog --query \"{query}\""
    stdout, stderr, code = run_command(cmd)

    if code != 0:
        print(f"❌ FAILED: Cannot query ClickHouse: {stderr}")
        return False

    count = int(stdout.strip())
    print(f"✅ Query log has {count} queries in the last 60 seconds")

    if count == 0:
        print("⚠️  WARNING: No queries found. Make sure the orders app is running.")
        return False

    return True


def test_agent_check():
    """Test if the ClickHouse integration check runs successfully."""
    print("\n" + "=" * 60)
    print("TEST 2: Running ClickHouse agent check")
    print("=" * 60)

    cmd = "agent check clickhouse -l info 2>&1 | tail -50"
    stdout, stderr, code = run_command(cmd)

    if "Running check clickhouse" in stdout:
        print("✅ ClickHouse check is running")
    else:
        print("❌ FAILED: ClickHouse check not running properly")
        print(stdout[-500:])  # Last 500 chars
        return False

    if "error" in stdout.lower() and "statement_sample" in stdout.lower():
        print("⚠️  WARNING: Errors found in check output:")
        print(stdout)
        return False

    return True


def test_agent_logs():
    """Check agent logs for statement sample activity."""
    print("\n" + "=" * 60)
    print("TEST 3: Checking agent logs for query samples")
    print("=" * 60)

    # Wait a bit for samples to be collected
    print("Waiting 15 seconds for sample collection...")
    time.sleep(15)

    cmd = "tail -100 /var/log/datadog/agent.log | grep -i 'statement_sample\\|query_sample\\|query log samples' | tail -20"
    stdout, stderr, code = run_command(cmd)

    if not stdout:
        print("⚠️  No statement sample logs found")
        print("Checking for any ClickHouse logs...")
        cmd = "tail -100 /var/log/datadog/agent.log | grep -i clickhouse | tail -10"
        stdout, _, _ = run_command(cmd)
        print(stdout if stdout else "No ClickHouse logs found")
        return False

    print("✅ Found statement sample activity in logs:")
    print(stdout)

    # Check for success indicators
    if "Loaded" in stdout and "rows from system.query_log" in stdout:
        print("✅ Query log samples are being fetched")
        return True

    if "submitted" in stdout.lower():
        print("✅ Samples are being submitted")
        return True

    return False


def test_metrics():
    """Check if statement sample metrics are being reported."""
    print("\n" + "=" * 60)
    print("TEST 4: Checking statement sample metrics")
    print("=" * 60)

    cmd = "agent status 2>&1 | grep -A 20 clickhouse | grep -i 'sample\\|query_log'"
    stdout, stderr, code = run_command(cmd)

    if stdout:
        print("✅ Found ClickHouse metrics:")
        print(stdout)
        return True
    else:
        print("⚠️  No statement sample metrics found in agent status")
        return False


def show_sample_queries():
    """Show sample queries from query_log."""
    print("\n" + "=" * 60)
    print("BONUS: Sample queries in ClickHouse query_log")
    print("=" * 60)

    query = """
    SELECT
        event_time,
        user,
        query_duration_ms,
        substring(query, 1, 100) as query_preview
    FROM system.query_log
    WHERE query NOT LIKE '%system.query_log%'
        AND event_time > now() - INTERVAL 60 SECOND
    ORDER BY event_time DESC
    LIMIT 10
    FORMAT Pretty
    """

    cmd = f"clickhouse-client --host clickhouse-primary --port 9000 --user datadog --password datadog --query \"{query}\""
    stdout, stderr, code = run_command(cmd)

    if code == 0:
        print(stdout)
    else:
        print(f"Could not fetch sample queries: {stderr}")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("CLICKHOUSE QUERY SAMPLES VERIFICATION")
    print("=" * 60)

    tests = [
        ("ClickHouse Query Log", test_clickhouse_query_log),
        ("Agent Check", test_agent_check),
        ("Agent Logs", test_agent_logs),
        ("Metrics", test_metrics),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ FAILED: {test_name} - {e}")
            results.append((test_name, False))

    # Show sample queries
    try:
        show_sample_queries()
    except Exception as e:
        print(f"Could not show sample queries: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Query samples should be working.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        print("\nTroubleshooting tips:")
        print("1. Make sure orders app is running and generating queries")
        print("2. Check that DBM is enabled in clickhouse.yaml")
        print("3. Verify datadog user has permissions on system.query_log")
        print("4. Check agent logs: tail -f /var/log/datadog/agent.log | grep clickhouse")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

