# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.base import _TrialErrorDowngrade, _TrialModeProxy

SERVICE = {
    "id": "svc1",
    "host": "10.0.0.1",
    "ports": [{"number": 8080, "name": ""}, {"number": 9090, "name": ""}],
}


class _FailingTrialCheck(AgentCheck):
    """Both candidates fail with an ERROR log + raised ConnectionError."""

    @classmethod
    def generate_configs(cls, service_dict):
        for p in service_dict["ports"]:
            yield {"target": f"{service_dict['host']}:{p['number']}"}

    def check(self, _):
        self.log.error("trial probe failed for %s", self.instance["target"])
        raise ConnectionError("connection refused")


class _WinOnSecondTrialCheck(AgentCheck):
    """First candidate (:8080) fails noisily, second (:9090) wins silently."""

    @classmethod
    def generate_configs(cls, service_dict):
        for p in service_dict["ports"]:
            yield {"target": f"{service_dict['host']}:{p['number']}"}

    def check(self, _):
        if not self.instance["target"].endswith(":9090"):
            self.log.error("trial probe failed for %s", self.instance["target"])
            raise ConnectionError("connection refused")
        if getattr(self, "_post_win", False):
            self.log.error("real winner error")
            raise ConnectionError("real failure")


class _NoCandidatesTrialCheck(AgentCheck):
    """generate_configs yields nothing."""

    @classmethod
    def generate_configs(cls, service_dict):
        return
        yield  # pragma: no cover - keeps the function a generator


def _make_proxy(target_cls, name):
    proxy = target_cls(name, {}, [{"__discovery_service__": SERVICE}])
    assert isinstance(proxy, _TrialModeProxy), "trial proxy dispatch did not fire"
    return proxy


def _check_logger(name):
    return logging.getLogger("datadog_checks.base.checks.base.{}".format(name))


def test_proxy_constructed_for_discovery_service():
    proxy = _FailingTrialCheck("t1", {}, [{"__discovery_service__": SERVICE}])
    assert isinstance(proxy, _TrialModeProxy)
    assert proxy._target_cls is _FailingTrialCheck
    assert proxy._service_dict == SERVICE


def test_trial_run_downgrades_error_logs_to_debug(caplog):
    proxy = _make_proxy(_FailingTrialCheck, "t_downgrade")

    with caplog.at_level(logging.DEBUG, logger="datadog_checks.base.checks.base.t_downgrade"):
        result = proxy.run()

    assert "no candidate accepted by check" in result
    probe_records = [r for r in caplog.records if "trial probe failed" in r.getMessage()]
    assert probe_records, "expected the candidate ERROR log to be captured (downgraded)"
    assert all(r.levelno == logging.DEBUG for r in probe_records), (
        "trial-mode candidate ERROR logs must be downgraded to DEBUG, got: "
        f"{[(r.levelname, r.getMessage()) for r in probe_records]}"
    )
    assert not any(r.levelno >= logging.ERROR for r in probe_records)


def test_trial_filter_removed_after_failed_candidate_runs():
    proxy = _make_proxy(_FailingTrialCheck, "t_cleanup_ok")
    proxy.run()

    logger = _check_logger("t_cleanup_ok")
    leftover = [f for f in logger.filters if isinstance(f, _TrialErrorDowngrade)]
    assert leftover == [], f"trial filter leaked onto logger: {logger.filters}"


def test_trial_filter_removed_on_unexpected_exception(monkeypatch):
    proxy = _make_proxy(_FailingTrialCheck, "t_cleanup_raise")

    original_run = AgentCheck.run

    def _boom(self):
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr(AgentCheck, "run", _boom)
    try:
        result = proxy.run()
    finally:
        monkeypatch.setattr(AgentCheck, "run", original_run)

    assert "simulated unexpected failure" in result
    logger = _check_logger("t_cleanup_raise")
    leftover = [f for f in logger.filters if isinstance(f, _TrialErrorDowngrade)]
    assert leftover == [], f"trial filter leaked onto logger: {logger.filters}"


def test_winner_run_errors_not_suppressed(caplog):
    proxy = _make_proxy(_WinOnSecondTrialCheck, "t_winner")

    with caplog.at_level(logging.DEBUG, logger="datadog_checks.base.checks.base.t_winner"):
        first = proxy.run()
    assert first == "", f"winning trial should return empty error report, got {first!r}"
    assert proxy._winner is not None

    # Switch the winner into "now produce a real error" mode and re-run.
    proxy._winner._post_win = True
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="datadog_checks.base.checks.base.t_winner"):
        second = proxy.run()

    assert "real failure" in second
    real_errors = [r for r in caplog.records if r.getMessage() == "real winner error"]
    assert real_errors, "winner's ERROR log should propagate (not be suppressed)"
    assert all(r.levelno == logging.ERROR for r in real_errors), (
        f"post-winner ERROR logs must NOT be downgraded, got: {[(r.levelname, r.getMessage()) for r in real_errors]}"
    )


def test_no_candidates_yielded_does_not_install_filter():
    proxy = _make_proxy(_NoCandidatesTrialCheck, "t_no_candidates")

    result = proxy.run()
    assert "generate_configs() yielded no candidates" in result

    logger = _check_logger("t_no_candidates")
    leftover = [f for f in logger.filters if isinstance(f, _TrialErrorDowngrade)]
    assert leftover == []


@pytest.mark.parametrize(
    "level_in,level_out",
    [
        (logging.CRITICAL, logging.DEBUG),
        (logging.ERROR, logging.DEBUG),
        (logging.WARNING, logging.WARNING),
        (logging.INFO, logging.INFO),
        (logging.DEBUG, logging.DEBUG),
    ],
)
def test_filter_downgrade_levels(level_in, level_out):
    f = _TrialErrorDowngrade()
    record = logging.LogRecord(name="x", level=level_in, pathname="x.py", lineno=1, msg="m", args=None, exc_info=None)
    assert f.filter(record) is True
    assert record.levelno == level_out
