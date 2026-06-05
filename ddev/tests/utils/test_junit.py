# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the JUnit XML parser."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from ddev.utils.junit import FailedTest, parse_junit_dir, parse_junit_failures

PASSING_AND_FAILING = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="4" failures="1" errors="1">
    <testcase classname="tests.test_a" name="test_pass"/>
    <testcase classname="tests.test_a" name="test_fail"><failure message="assert 1 == 2">trace</failure></testcase>
    <testcase classname="tests.test_b" name="test_err"><error message="boom">trace</error></testcase>
    <testcase classname="tests.test_c" name="test_skip"><skipped/></testcase>
  </testsuite>
</testsuites>
"""

ALL_PASSING = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="1" failures="0">
  <testcase classname="tests.test_a" name="test_ok"/>
</testsuite>
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_junit_failures_returns_failures_and_errors(tmp_path: Path) -> None:
    failures = parse_junit_failures(_write(tmp_path, "report.xml", PASSING_AND_FAILING))

    assert failures == [
        FailedTest(classname="tests.test_a", name="test_fail", message="assert 1 == 2", kind="failure"),
        FailedTest(classname="tests.test_b", name="test_err", message="boom", kind="error"),
    ]


def test_failed_test_identifier() -> None:
    assert FailedTest("tests.test_a", "test_fail", None, "failure").identifier == "tests.test_a::test_fail"
    assert FailedTest(None, "test_fail", None, "failure").identifier == "test_fail"


def test_parse_junit_failures_no_failures(tmp_path: Path) -> None:
    assert parse_junit_failures(_write(tmp_path, "report.xml", ALL_PASSING)) == []


def test_parse_junit_failures_malformed_raises(tmp_path: Path) -> None:
    with pytest.raises(ET.ParseError):
        parse_junit_failures(_write(tmp_path, "bad.xml", "<testsuite><testcase>"))


def test_parse_junit_failures_rejects_dtd(tmp_path: Path) -> None:
    doc = '<?xml version="1.0"?>\n<!DOCTYPE root [<!ENTITY x "y">]>\n<testsuite></testsuite>'
    with pytest.raises(ValueError, match="DTD/entity"):
        parse_junit_failures(_write(tmp_path, "xxe.xml", doc))


def test_parse_junit_dir_aggregates_and_skips_bad_files(tmp_path: Path) -> None:
    _write(tmp_path, "a.xml", PASSING_AND_FAILING)
    _write(tmp_path, "b.xml", ALL_PASSING)
    _write(tmp_path, "bad.xml", "<not-closed>")
    nested = tmp_path / "nested"
    nested.mkdir()
    _write(nested, "c.xml", PASSING_AND_FAILING)

    failures = parse_junit_dir(tmp_path)

    assert [f.name for f in failures] == ["test_fail", "test_err", "test_fail", "test_err"]
