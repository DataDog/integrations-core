# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import json
import threading
from unittest.mock import Mock, patch

from datadog_checks.argocd import ArgocdCheck
from datadog_checks.argocd.resources import ArgocdResourceCollector
from datadog_checks.argocd.stream_listener import ArgocdApplicationStreamListener


def _instance(**overrides) -> dict:
    instance = {
        "app_controller_endpoint": "http://app_controller:8082",
        "collect_genresources": True,
        "genresources_endpoint": "https://argocd.example.com",
        "genresources_auth_token": "test-token",
    }
    instance.update(overrides)
    return instance


def _application(name: str, *, namespace: str = "argocd", resource_version: str = "100") -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace, "resourceVersion": resource_version},
        "spec": {"destination": {"server": "https://kubernetes.default.svc"}, "source": {}},
        "status": {"sync": {"status": "Synced"}},
    }


def _listener(collector) -> ArgocdApplicationStreamListener:
    return ArgocdApplicationStreamListener(
        Mock(), collector, endpoint="https://argocd.example.com", auth_token=None, backoff_max_seconds=10
    )


def _event(event_type: str, application: dict) -> bytes:
    return json.dumps({"result": {"type": event_type, "application": application}}).encode()


def _check(**overrides) -> ArgocdCheck:
    """Build an ArgocdCheck with config models loaded and the genresources collector attached.

    Production builds the collector lazily on the first ``check()`` once
    ``check_initializations`` has populated ``self.config``; tests reach into
    ``check._resource_collector`` directly, so we mirror that bootstrap here.
    """
    check = ArgocdCheck("argocd", {}, [_instance(**overrides)])
    check.load_configuration_models()
    check._resource_collector = ArgocdResourceCollector(check)
    return check


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


def test_emit_stream_application_dedupes_unchanged_app():
    check = _check(genresources_stream_applications_enabled=True)
    app = _application("web", resource_version="100")

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.emit_stream_application(app)
        check._resource_collector.emit_stream_application(app)  # same resourceVersion -> deduped

    assert submit.call_count == 1


def test_forget_application_lets_a_readded_app_resubmit():
    check = _check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector
    app = _application("web", resource_version="100")

    with patch.object(check, "submit_generic_resource") as submit:
        collector.emit_stream_application(app)  # submit #1
        collector.forget_application(app)  # DELETED -> dropped from the dedup cache
        collector.emit_stream_application(app)  # re-added -> submit #2

    assert submit.call_count == 2


def test_collect_with_streaming_off_runs_poll_path_and_starts_no_listener():
    check = _check()  # streaming defaults off
    collector = check._resource_collector

    with patch("datadog_checks.argocd.resources.ArgocdApplicationStreamListener") as listener_cls:
        with patch.object(collector, "_collect_type") as collect_type:
            collector.collect()

    listener_cls.assert_not_called()
    assert collector._listener is None
    assert collect_type.call_count == 3  # poll path collected all three resource types


def test_collect_with_streaming_on_starts_listener_and_rescrapes_all_types():
    check = _check(genresources_stream_applications_enabled=True)
    collector = check._resource_collector

    with patch("datadog_checks.argocd.resources.ArgocdApplicationStreamListener") as listener_cls:
        listener_cls.return_value.is_alive.return_value = False
        with patch.object(collector, "_collect_type") as collect_type:
            collector.collect()

    listener_cls.return_value.start.assert_called_once()
    assert collect_type.call_count == 3  # the first full rescrape covers all three types


def test_stream_run_backs_off_exponentially_and_caps():
    listener = _listener(Mock())  # backoff_max_seconds=10
    waits: list[float] = []

    def fake_stream_once():
        raise ConnectionError("boom")

    def fake_sleep(seconds):
        waits.append(seconds)
        if len(waits) >= 5:
            listener._stop.set()

    listener._stream_once = fake_stream_once
    listener._sleep = fake_sleep
    listener._run()

    assert waits == [1, 2, 4, 8, 10]  # doubles each reconnect, then caps at backoff_max_seconds


def test_stream_run_backs_off_on_clean_disconnect_without_data():
    # A server that returns 200 then immediately closes (no data) must NOT become a hot reconnect loop.
    listener = _listener(Mock())
    waits: list[float] = []

    def fake_stream_once():
        return False  # clean return, no data delivered

    def fake_sleep(seconds):
        waits.append(seconds)
        if len(waits) >= 3:
            listener._stop.set()

    listener._stream_once = fake_stream_once
    listener._sleep = fake_sleep
    listener._run()

    assert waits == [1, 2, 4]  # still backs off on a clean, data-less disconnect


def test_stream_run_resets_backoff_after_a_connection_that_received_data():
    listener = _listener(Mock())
    waits: list[float] = []
    results = iter([False, False, True, False])  # two empty connects, one with data, then empty

    def fake_stream_once():
        return next(results)

    def fake_sleep(seconds):
        waits.append(seconds)
        if len(waits) >= 4:
            listener._stop.set()

    listener._stream_once = fake_stream_once
    listener._sleep = fake_sleep
    listener._run()

    assert waits == [1, 2, 1, 1]  # grows while empty, resets to 1 after the connection that got data


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
    check.http.get.return_value = _Resp()
    listener = ArgocdApplicationStreamListener(
        check, collector, endpoint="https://argocd.example.com", auth_token=None, backoff_max_seconds=1
    )

    listener.start()
    try:
        assert processed.wait(timeout=5)  # the streamed line reached the collector
    finally:
        listener.cancel()
        listener.join(timeout=5)

    assert not listener.is_alive()  # cancel() closed the stream, unblocked iter_lines, and the thread exited
