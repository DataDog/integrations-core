# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the JUnit XML parser."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from defusedxml.common import EntitiesForbidden
from defusedxml.ElementTree import ParseError

from ddev.utils.junit import (
    JUnitProperty,
    JUnitResultKind,
    TestStatus,
    parse_junit_dir,
    parse_junit_report,
)

# A full xunit2 report: 4 tests, one each of pass/fail/error/skip, with suite properties + timestamp.
FULL_REPORT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites name="run">
  <testsuite name="pytest" tests="4" failures="1" errors="1" skipped="1" time="1.5" \
timestamp="2026-07-13T09:00:00" hostname="runner-1">
    <properties>
      <property name="python" value="3.13"/>
    </properties>
    <testcase classname="tests.test_a" name="test_pass" time="0.1"/>
    <testcase classname="tests.test_a" name="test_fail" time="0.2">\
<failure message="assert 1 == 2" type="AssertionError">trace-f</failure></testcase>
    <testcase classname="tests.test_b" name="test_err" time="0.3">\
<error message="boom" type="RuntimeError">trace-e</error></testcase>
    <testcase classname="tests.test_c" name="test_skip" time="0.0"><skipped message="no reason"/></testcase>
  </testsuite>
</testsuites>
"""

# A bare <testsuite> root (pytest emits this form too); no <testsuites> wrapper, so no report name.
BARE_SUITE = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0">
  <testcase classname="tests.test_a" name="test_ok"/>
</testsuite>
"""

ENTITY_DOC = '<?xml version="1.0"?>\n<!DOCTYPE root [<!ENTITY x "y">]>\n<testsuite>&x;</testsuite>'


def write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_report_structure_and_counts(tmp_path: Path) -> None:
    report = parse_junit_report(write(tmp_path, "report.xml", FULL_REPORT))

    assert report.name == "run"
    assert len(report.test_suites) == 1
    suite = report.test_suites[0]

    assert suite.name == "pytest"
    assert (suite.reported_counts.tests, suite.reported_counts.failures) == (4, 1)
    assert (suite.reported_counts.errors, suite.reported_counts.skipped) == (1, 1)
    assert suite.reported_counts.passed == 1
    assert suite.time == 1.5
    assert suite.timestamp == datetime(2026, 7, 13, 9, 0, 0)
    assert suite.hostname == "runner-1"
    assert suite.properties == (JUnitProperty(name="python", value="3.13"),)


def test_parse_report_test_cases(tmp_path: Path) -> None:
    suite = parse_junit_report(write(tmp_path, "report.xml", FULL_REPORT)).test_suites[0]
    by_name = {case.name: case for case in suite.test_cases}

    assert len(suite.test_cases) == 4
    assert by_name["test_pass"].status == TestStatus.PASSED
    assert by_name["test_pass"].identifier == "tests.test_a::test_pass"
    assert by_name["test_pass"].results == ()

    fail = by_name["test_fail"]
    assert fail.status == TestStatus.FAILED
    assert fail.time == 0.2
    assert fail.results[0].kind == JUnitResultKind.FAILURE
    assert fail.results[0].message == "assert 1 == 2"
    assert fail.results[0].type == "AssertionError"
    assert fail.results[0].text == "trace-f"

    assert by_name["test_err"].status == TestStatus.ERROR
    assert by_name["test_err"].results[0].kind == JUnitResultKind.ERROR
    assert by_name["test_skip"].status == TestStatus.SKIPPED
    assert by_name["test_skip"].results[0].kind == JUnitResultKind.SKIPPED


def test_parse_bare_testsuite_root(tmp_path: Path) -> None:
    report = parse_junit_report(write(tmp_path, "report.xml", BARE_SUITE))

    assert report.name is None
    assert len(report.test_suites) == 1
    suite = report.test_suites[0]
    assert suite.reported_counts.passed == 1
    assert suite.timestamp is None
    assert suite.hostname is None
    assert suite.test_cases[0].status == TestStatus.PASSED


def test_parse_report_malformed_raises(tmp_path: Path) -> None:
    with pytest.raises(ParseError):
        parse_junit_report(write(tmp_path, "bad.xml", "<testsuite><testcase>"))


def test_parse_report_rejects_entities(tmp_path: Path) -> None:
    with pytest.raises(EntitiesForbidden):
        parse_junit_report(write(tmp_path, "xxe.xml", ENTITY_DOC))


def test_parse_report_rejects_non_junit_root(tmp_path: Path) -> None:
    # A Cobertura coverage.xml shares the artifact directory; it must not be read as a test suite.
    with pytest.raises(ValueError, match="Not a JUnit report"):
        parse_junit_report(write(tmp_path, "coverage.xml", '<coverage version="1"/>'))


def test_parse_junit_dir_aggregates_and_skips_bad_files(tmp_path: Path) -> None:
    write(tmp_path, "a.xml", FULL_REPORT)
    write(tmp_path, "b.xml", BARE_SUITE)
    write(tmp_path, "bad.xml", "<not-closed>")
    write(tmp_path, "xxe.xml", ENTITY_DOC)
    nested = tmp_path / "nested"
    nested.mkdir()
    write(nested, "c.xml", FULL_REPORT)

    reports = parse_junit_dir(tmp_path)

    # a.xml, b.xml, nested/c.xml parse; bad.xml (malformed) and xxe.xml (entities) are skipped.
    assert len(reports) == 3
    total_passed = sum(suite.reported_counts.passed for report in reports for suite in report.test_suites)
    total_failed = sum(suite.reported_counts.failures for report in reports for suite in report.test_suites)
    assert total_passed == 3  # 1 (a) + 1 (b) + 1 (c)
    assert total_failed == 2  # 1 (a) + 1 (c)


def test_parse_junit_dir_empty(tmp_path: Path) -> None:
    assert parse_junit_dir(tmp_path) == []
