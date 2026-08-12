# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import json
import threading
import time
from unittest.mock import Mock, patch

import pytest

from datadog_checks.argocd.resources import APPLICATION_SPEC
from datadog_checks.argocd.resources_constants import (
    GENRESOURCES_API_UP_METRIC,
    GENRESOURCES_STREAM_EVENTS_METRIC,
    GENRESOURCES_STREAM_RECONNECTS_METRIC,
    GENRESOURCES_STREAM_UP_METRIC,
)
from datadog_checks.argocd.stream_listener import ArgocdApplicationStreamListener
from datadog_checks.dev.utils import get_metadata_metrics

from .common import GENRESOURCES_ENDPOINT, build_check

pytestmark = pytest.mark.unit


def _application(name: str, *, namespace: str = "argocd", resource_version: str = "100") -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace, "resourceVersion": resource_version},
        "spec": {"destination": {"server": "https://kubernetes.default.svc"}, "source": {}},
        "status": {"sync": {"status": "Synced"}},
    }


def _listener(collector, *, check=None) -> ArgocdApplicationStreamListener:
    return ArgocdApplicationStreamListener(
        check or Mock(),
        collector,
        endpoint=GENRESOURCES_ENDPOINT,
        auth_token=None,
        backoff_max_seconds=10,
        read_timeout_seconds=60,
        http=Mock(),
    )


def _event(event_type: str, application: dict) -> bytes:
    return json.dumps({"result": {"type": event_type, "application": application}}).encode()


def _run_stream_and_record_waits(listener, outcomes, stop_after: int) -> list[float]:
    """Drive listener._run() over a scripted sequence of _stream_once() return values, recording each wait.

    Each outcome is a bool: True = the connection received data, False = it disconnected with none.
    _stream_once catches connection errors internally, so an error is reported as a False return (never
    raised). The listener stops itself once ``stop_after`` waits have been recorded.
    """
    waits: list[float] = []
    results = iter(outcomes)

    def fake_stream_once():
        return next(results)

    def fake_sleep(seconds):
        waits.append(seconds)
        if len(waits) >= stop_after:
            listener._stop.set()

    listener._stream_once = fake_stream_once
    listener._sleep = fake_sleep
    listener._run()
    return waits


def test_handle_line_routes_added_and_deleted_to_the_collector():
    collector = Mock()
    listener = _listener(collector)
    app = _application("web")

    listener._handle_line(_event("ADDED", app))
    listener._handle_line(_event("DELETED", app))

    collector.emit_stream_application.assert_called_once_with(app)
    collector.forget_application.assert_called_once_with(app)


def test_handle_line_ignores_malformed_and_non_application_frames():
    collector = Mock()
    listener = _listener(collector)

    for line in [
        b"not json",
        json.dumps({"error": {"message": "boom"}}).encode(),  # gRPC-gateway error frame
        json.dumps({"result": {"type": "ADDED"}}).encode(),  # no application
    ]:
        listener._handle_line(line)

    collector.emit_stream_application.assert_not_called()
    collector.forget_application.assert_not_called()


def test_handle_line_ignores_bookmark_and_unknown_event_types():
    collector = Mock()
    listener = _listener(collector)
    app = _application("web")

    listener._handle_line(_event("BOOKMARK", app))
    listener._handle_line(_event("SOMETHING_ELSE", app))

    collector.emit_stream_application.assert_not_called()  # only ADDED/MODIFIED emit
    collector.forget_application.assert_not_called()  # only DELETED forgets


def test_emit_stream_application_dedupes_unchanged_app():
    check = build_check(genresources_stream_applications_enabled=True)
    app = _application("web", resource_version="100")

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.emit_stream_application(app)
        check._resource_collector.emit_stream_application(app)  # same resourceVersion -> deduped

    assert submit.call_count == 1


def test_forget_application_lets_a_readded_app_resubmit():
    check = build_check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector
    app = _application("web", resource_version="100")

    with patch.object(check, "submit_generic_resource") as submit:
        collector.emit_stream_application(app)  # submit #1
        collector.forget_application(app)  # DELETED -> dropped from the dedup cache
        collector.emit_stream_application(app)  # re-added -> submit #2

    assert submit.call_count == 2


def test_forget_application_during_a_concurrent_full_scrape_is_not_resurrected():
    check = build_check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector
    app = _application("web", resource_version="100")

    with (
        patch.object(check, "submit_generic_resource") as submit,
        patch.object(collector, "_fetch", return_value=[app]),
    ):
        seen_at = int(time.time())  # the full scrape's snapshot is treated as taken at-or-before this instant
        collector.forget_application(app)  # DELETED frame processed after the snapshot was taken
        collector._collect_type(APPLICATION_SPEC, seen_at=seen_at, expire_at=seen_at + 1800, force_full=True)

    submit.assert_not_called()  # the stale, pre-delete snapshot must not resurrect it


def test_collect_with_streaming_off_runs_poll_path_and_starts_no_listener():
    check = build_check(genresources_stream_applications_enabled=False)
    collector = check._resource_collector

    with patch("datadog_checks.argocd.resources.ArgocdApplicationStreamListener") as listener_cls:
        with patch.object(collector, "_collect_type") as collect_type:
            collector.collect()

    listener_cls.assert_not_called()
    assert collector._listener is None
    assert collect_type.call_count == 3  # poll path collected all three resource types


def test_collect_with_streaming_on_starts_listener_and_rescrapes_all_types():
    check = build_check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector

    with patch("datadog_checks.argocd.resources.ArgocdApplicationStreamListener") as listener_cls:
        listener_cls.return_value.is_alive.return_value = False
        with patch.object(collector, "_collect_type") as collect_type:
            collector.collect()

    listener_cls.return_value.start.assert_called_once()
    assert collect_type.call_count == 3  # the first full rescrape covers all three types


def test_ensure_listener_gives_the_listener_its_own_http_session():
    check = build_check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector

    with patch("datadog_checks.argocd.resources.ArgocdApplicationStreamListener") as listener_cls:
        listener_cls.return_value.is_alive.return_value = False
        collector._ensure_listener()

    http = listener_cls.call_args.kwargs["http"]
    assert http is not None
    assert http is not check.http  # a dedicated HTTP client, not the check's shared client


def test_ensure_listener_passes_the_configured_read_timeout():
    check = build_check(genresources_stream_applications_enabled=True, genresources_stream_read_timeout_seconds=123)
    collector = check._resource_collector

    with patch("datadog_checks.argocd.resources.ArgocdApplicationStreamListener") as listener_cls:
        listener_cls.return_value.is_alive.return_value = False
        collector._ensure_listener()

    assert listener_cls.call_args.kwargs["read_timeout_seconds"] == 123


def test_collect_with_stream_emits_stream_up_one_when_the_listener_is_connected(aggregator):
    check = build_check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector

    with patch("datadog_checks.argocd.resources.ArgocdApplicationStreamListener") as listener_cls:
        listener_cls.return_value.is_alive.return_value = True
        listener_cls.return_value.is_connected.return_value = True
        with patch.object(collector, "_collect_type"):
            collector.collect()

    aggregator.assert_metric(GENRESOURCES_STREAM_UP_METRIC, value=1)


def test_collect_with_stream_emits_stream_up_zero_even_when_scrapes_are_throttled(aggregator):
    check = build_check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector
    now = time.time()
    collector._last_app_full = now  # within every scrape interval -> nothing is fetched this cycle
    collector._last_cluster_scrape = now
    collector._last_repository_scrape = now

    with patch("datadog_checks.argocd.resources.ArgocdApplicationStreamListener") as listener_cls:
        listener_cls.return_value.is_alive.return_value = True
        listener_cls.return_value.is_connected.return_value = False
        with patch.object(collector, "_collect_type") as collect_type:
            collector.collect()

    collect_type.assert_not_called()  # every per-type scrape was throttled...
    aggregator.assert_metric(GENRESOURCES_STREAM_UP_METRIC, value=0)  # ...but stream.up is still emitted every cycle


def test_stop_signals_cancel_without_joining():
    check = build_check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector
    listener = Mock()
    collector._listener = listener

    collector.stop()

    listener.cancel.assert_called_once()
    listener.join.assert_not_called()  # cancel() must not block the unschedule on a join


def test_ensure_listener_does_not_start_a_listener_after_stop():
    check = build_check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector
    collector.stop()  # cancel arrived before the first collection cycle created a listener

    with patch("datadog_checks.argocd.resources.ArgocdApplicationStreamListener") as listener_cls:
        with patch.object(collector, "_collect_type"):
            collector.collect()

    listener_cls.assert_not_called()
    assert collector._listener is None


def test_collect_throttles_the_missing_endpoint_warning_but_still_emits_api_up(aggregator, caplog):
    check = build_check(genresources_endpoint=None)
    collector = check._resource_collector

    collector.collect()
    collector.collect()  # second call within the collection interval

    warnings = [r for r in caplog.records if "genresources_endpoint is not set" in r.message]
    assert len(warnings) == 1  # the warning is throttled to once per collection interval
    # api.up=0 is still emitted every cycle for all three types (no metric gaps): 3 types x 2 cycles
    aggregator.assert_metric(GENRESOURCES_API_UP_METRIC, value=0, count=6)


def test_stream_once_survives_a_frame_that_raises_and_keeps_the_connection():
    check = build_check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector
    bad = json.dumps({"result": {"type": "ADDED", "application": {"metadata": "not-a-dict"}}}).encode()
    good = _event("ADDED", _application("web"))

    class _Resp:
        def raise_for_status(self):
            pass

        def iter_lines(self):
            yield bad  # _change_token raises AttributeError on the non-dict metadata
            yield good

        def close(self):
            pass

    http = Mock()
    http.get.return_value = _Resp()
    listener = ArgocdApplicationStreamListener(
        check,
        collector,
        endpoint=GENRESOURCES_ENDPOINT,
        auth_token=None,
        backoff_max_seconds=10,
        read_timeout_seconds=60,
        http=http,
    )

    with patch.object(check, "submit_generic_resource") as submit:
        got_data = listener._stream_once()

    assert got_data is True  # the bad frame did not tear down the connection
    assert submit.call_count == 1  # the following good frame was still processed


def test_stream_once_reports_data_received_even_when_the_connection_then_errors():
    # A connection that delivers a line and THEN drops (read timeout / reset) must still report got_data=True,
    # so the supervisor resets backoff instead of treating a healthy stream as a dead one.
    check = build_check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector

    class _Resp:
        def raise_for_status(self):
            pass

        def iter_lines(self):
            yield _event("ADDED", _application("web"))
            raise ConnectionError("stream dropped after delivering data")

        def close(self):
            pass

    http = Mock()
    http.get.return_value = _Resp()
    listener = ArgocdApplicationStreamListener(
        check,
        collector,
        endpoint=GENRESOURCES_ENDPOINT,
        auth_token=None,
        backoff_max_seconds=10,
        read_timeout_seconds=60,
        http=http,
    )

    with patch.object(check, "submit_generic_resource"):
        got_data = listener._stream_once()

    assert got_data is True  # data arrived before the drop; _stream_once caught the error and reported it


def test_stream_once_inherits_http_client_auth_when_no_token():
    check = build_check(genresources_stream_applications_enabled=True, genresources_auth_token=None)
    collector = check._resource_collector

    class _Resp:
        def raise_for_status(self):
            pass

        def iter_lines(self):
            return iter(())

        def close(self):
            pass

    http = Mock()
    http.get.return_value = _Resp()
    listener = ArgocdApplicationStreamListener(
        check,
        collector,
        endpoint=GENRESOURCES_ENDPOINT,
        auth_token=None,
        backoff_max_seconds=10,
        read_timeout_seconds=60,
        http=http,
    )

    listener._stream_once()

    kwargs = http.get.call_args.kwargs
    assert "headers" not in kwargs  # must not clobber the HTTP client's configured auth
    assert (
        "extra_headers" not in kwargs
    )  # omit entirely -- even empty extra_headers would drop the inherited auth_token


def test_handle_line_emits_events_received_metric_matching_metadata(aggregator):
    check = build_check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector
    listener = _listener(collector, check=check)

    with patch.object(check, "submit_generic_resource"):
        listener._handle_line(_event("ADDED", _application("web")))

    aggregator.assert_metric(GENRESOURCES_STREAM_EVENTS_METRIC, value=1, count=1)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_run_counts_a_reconnect_on_disconnect(aggregator):
    check = build_check(genresources_stream_applications_enabled=True)
    listener = _listener(check._resource_collector, check=check)

    _run_stream_and_record_waits(listener, [False], stop_after=1)  # one clean disconnect, then stop

    aggregator.assert_metric(GENRESOURCES_STREAM_RECONNECTS_METRIC, value=1, count=1)


def test_stream_run_backs_off_exponentially_and_caps():
    # A data-less disconnect -- a clean 200-then-close or a connection error (which _stream_once reports as
    # a False return) -- backs off exponentially and must NOT become a hot reconnect loop.
    waits = _run_stream_and_record_waits(_listener(Mock()), [False] * 5, stop_after=5)
    assert waits == [1, 2, 4, 8, 10]  # doubles each reconnect, then caps at backoff_max_seconds


def test_stream_run_resets_backoff_after_a_connection_that_received_data():
    waits = _run_stream_and_record_waits(_listener(Mock()), [False, False, True, False], stop_after=4)
    assert waits == [1, 2, 1, 1]  # grows while empty, resets to 1 after the connection that received data


def test_listener_thread_routes_a_line_then_shuts_down_cleanly_on_cancel():
    collector = Mock()
    processed = threading.Event()
    collector.emit_stream_application.side_effect = lambda app: processed.set()
    block = threading.Event()

    class _Resp:
        def raise_for_status(self):
            pass

        def iter_lines(self):
            yield _event("ADDED", {"metadata": {"name": "web", "namespace": "argocd"}})
            block.wait()  # hold the stream open like a live idle connection until cancel() closes it
            raise OSError("connection closed")

        def close(self):
            block.set()

    check = Mock()
    http = Mock()
    http.get.return_value = _Resp()
    listener = ArgocdApplicationStreamListener(
        check,
        collector,
        endpoint=GENRESOURCES_ENDPOINT,
        auth_token=None,
        backoff_max_seconds=1,
        read_timeout_seconds=60,
        http=http,
    )

    listener.start()
    try:
        assert processed.wait(timeout=5)  # the streamed line reached the collector
    finally:
        listener.cancel()
        listener.join(timeout=5)

    assert not listener.is_alive()  # cancel() closed the stream, unblocked iter_lines, and the thread exited
