# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.control_m.config_models import ConfigMixin

if TYPE_CHECKING:
    from collections.abc import Callable

    from requests import Response

_SERVICE_CHECK_CAN_LOGIN = "can_login"
_SERVICE_CHECK_CAN_CONNECT = "can_connect"
_STATUS_NORMALIZATION = {
    "ended ok": "ended_ok",
    "ended not ok": "ended_not_ok",
    "executing": "executing",
    "wait condition": "wait_condition",
    "waiting for condition": "wait_condition",
    "wait event": "wait_event",
    "waiting for event": "wait_event",
    "wait user": "wait_user",
    "waiting for user": "wait_user",
    "wait resource": "wait_resource",
    "waiting for resource": "wait_resource",
    "wait host": "wait_host",
    "waiting for host": "wait_host",
    "wait workload": "wait_workload",
    "waiting for workload": "wait_workload",
    "canceled": "canceled",
    "cancelled": "canceled",
}
_TERMINAL_STATUSES = {"ended_ok", "ended_not_ok", "canceled"}
_WAITING_STATUSES = {"wait_condition", "wait_event", "wait_user", "wait_resource", "wait_host", "wait_workload"}
_UP_STATES = {"up", "available", "connected", "active"}
_FINALIZED_RUNS_CACHE_KEY = "finalized_runs_control_m"
_ACTIVE_RUNS_CACHE_KEY = "active_runs_control_m"


class ControlMCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = "control_m"

    def __init__(self, name: str, init_config: dict[str, Any], instances: list[dict[str, Any]]) -> None:
        super().__init__(name, init_config, instances)

        self._configure_auth()
        self._configure_collection()

        self._base_tags = [f"control_m_instance:{self._api_endpoint}"]

        self._finalized_runs = {}
        self._active_runs = {}
        self._load_finalized_runs_cache()
        self._load_active_runs_cache()

    def _configure_auth(self) -> None:
        self._api_endpoint = self.instance.get("control_m_api_endpoint", "").rstrip("/")
        if not self._api_endpoint:
            raise ConfigurationError("`control_m_api_endpoint` is required")

        # Static tokens can be created that have no expiration. This is the ideal approach for production.
        # But we can support both. The logic here is that we'll try first with a static token and if it fails,
        # we fall back to session login.
        headers = self.instance.get("headers", {})
        self._has_static_token = any(k.lower() == "authorization" for k in headers)

        self._username = self.instance.get("control_m_username")
        self._password = self.instance.get("control_m_password")
        self._has_credentials = bool(self._username and self._password)

        if not self._has_static_token and not self._has_credentials:
            if self._username or self._password:
                raise ConfigurationError(
                    "`control_m_username` and `control_m_password` must both be set or both be omitted"
                )
            raise ConfigurationError(
                "No authentication configured. Provide `headers` with an API token "
                "or both `control_m_username` and `control_m_password`"
            )

        self._use_session_login = not self._has_static_token and self._has_credentials
        self._token_lifetime = self.instance.get("token_lifetime_seconds", 1800)
        self._token_refresh_buffer = self.instance.get("token_refresh_buffer_seconds", 300)
        if self._token_refresh_buffer >= self._token_lifetime:
            self._token_refresh_buffer = self._token_lifetime // 6
            self.log.warning(
                "token_refresh_buffer_seconds >= token_lifetime_seconds; clamping refresh buffer to %d seconds",
                self._token_refresh_buffer,
            )

        self._token = None
        self._token_expiration = 0.0
        self._static_token_retry_after = 0.0
        self._static_token_retry_interval = 300.0

    def _configure_collection(self) -> None:
        self._job_status_limit = int(self.instance.get("job_status_limit", 10000))
        self._job_name_filter = self.instance.get("job_name_filter", "*")
        self._finalized_ttl_seconds = int(self.instance.get("finalized_ttl_seconds", 86400))
        self._active_ttl_seconds = int(self.instance.get("active_ttl_seconds", 21600))
        query = {"limit": self._job_status_limit, "jobname": self._job_name_filter}
        self._jobs_status_url = f"{self._api_endpoint}/run/jobs/status?{urlencode(query)}"

    def _login(self) -> None:
        url = f"{self._api_endpoint}/session/login"
        payload = {"username": self._username, "password": self._password}

        try:
            response = self.http.post(url, json=payload)
        except OSError:
            self.log.error("Could not reach Control-M API at %s", url)
            raise

        if not response.ok:
            self.log.error("Control-M authentication failed (HTTP %s): %s", response.status_code, response.text)
            response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            self.log.error("Login response is not valid JSON: %s", response.text)
            raise

        token = data.get("token")
        if not token:
            raise ValueError(f"Login response did not contain a 'token' field: {data!r}")

        self._token = token
        self._token_expiration = time.monotonic() + self._token_lifetime
        self.log.debug("Obtained Control-M API token (valid for %d minutes)", self._token_lifetime // 60)

    def _ensure_token(self) -> None:
        # Used in session login mode only. Refresh the token if it's about to expire.
        remaining = self._token_expiration - time.monotonic()
        if self._token is not None and remaining > self._token_refresh_buffer:
            return
        self.log.info("Refreshing Control-M API token")
        self._login()

    def _make_request(self, method: str, url: str, **kwargs: Any) -> Response:
        request_fn = getattr(self.http, method)

        if self._use_session_login:
            if self._has_static_token and time.monotonic() >= self._static_token_retry_after:
                self.log.info("Retrying static token after cooldown")
                self._use_session_login = False
            else:
                return self._make_session_request(request_fn, url, **kwargs)

        response = request_fn(url, **kwargs)

        if response.status_code != 401:
            return response

        if not self._has_credentials:
            self.log.error("Token auth returned 401 and no credentials are configured for fallback")
            return response

        self.log.warning("Token auth returned 401; falling back to session login")
        self._use_session_login = True
        self._static_token_retry_after = time.monotonic() + self._static_token_retry_interval
        return self._make_session_request(request_fn, url, **kwargs)

    def _make_session_request(self, request_fn: Callable[..., Response], url: str, **kwargs: Any) -> Response:
        # Used in session login mode only. Make a request to the API using the session token.
        self._ensure_token()
        extra = {"Authorization": f"Bearer {self._token}"}
        response = request_fn(url, extra_headers=extra, **kwargs)

        if response.status_code == 401 and self._token is not None:
            self.log.info("Session token rejected (401); refreshing and retrying")
            self._token = None
            self._ensure_token()
            extra = {"Authorization": f"Bearer {self._token}"}
            response = request_fn(url, extra_headers=extra, **kwargs)

        return response

    def _auth_method_tag(self) -> str:
        # Added to keep track of which authentication method is being used.
        if self._use_session_login:
            return "auth_method:session_login"
        return "auth_method:static_token"

    def _auth_tags(self) -> list[str]:
        return self._base_tags + [self._auth_method_tag()]

    def _collect_server_health(self, servers: Any) -> None:
        # Collect server health from the Control-M API. 1 is up, 0 is down.
        if not isinstance(servers, list):
            return

        for server in servers:
            ctm_server = server.get("name") or server.get("ctm") or server.get("server") or "unknown"
            raw_state = str(server.get("state", "unknown"))
            state_tag = raw_state.lower().replace(" ", "_")
            is_up = 1 if state_tag in _UP_STATES else 0
            tags = self._base_tags + [f"ctm_server:{ctm_server}", f"state:{state_tag}"]
            self.gauge("server.up", is_up, tags=tags)

    def check(self, _: Any) -> None:
        auth_tags = self._auth_tags()

        if self._use_session_login:
            try:
                self._ensure_token()
            except Exception as e:
                self.service_check(
                    _SERVICE_CHECK_CAN_LOGIN,
                    self.CRITICAL,
                    tags=auth_tags,
                    message=f"Failed to authenticate to Control-M API: {e}",
                )
                self.service_check(
                    _SERVICE_CHECK_CAN_CONNECT,
                    self.CRITICAL,
                    tags=auth_tags,
                    message=f"Failed to authenticate to Control-M API: {e}",
                )
                self.gauge("can_login", 0, tags=auth_tags)
                self.gauge("can_connect", 0, tags=auth_tags)
                raise
            self.service_check(_SERVICE_CHECK_CAN_LOGIN, self.OK, tags=auth_tags)
            self.gauge("can_login", 1, tags=auth_tags)
        try:
            response = self._make_request("get", f"{self._api_endpoint}/config/servers")
            response.raise_for_status()
            servers = response.json()
        except Exception as e:
            auth_tags = self._auth_tags()
            self.service_check(
                _SERVICE_CHECK_CAN_CONNECT,
                self.CRITICAL,
                tags=auth_tags,
                message=f"Failed to connect to Control-M API: {e}",
            )
            self.gauge("can_connect", 0, tags=auth_tags)
            raise

        auth_tags = self._auth_tags()
        self.service_check(_SERVICE_CHECK_CAN_CONNECT, self.OK, tags=auth_tags)
        self.gauge("can_connect", 1, tags=auth_tags)

        self._collect_server_health(servers)
        self._collect_metadata(servers)
        self._collect_job_statuses()

    def _collect_job_statuses(self) -> None:
        url = self._jobs_status_url
        try:
            response = self._make_request("get", url)
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            self.log.warning("Unable to collect job statuses from /run/jobs/status: %s", e)
            return

        if not isinstance(payload, dict):
            return

        statuses = payload.get("statuses", [])
        total = payload.get("total")
        if total is not None:
            self.gauge("jobs.total", total, tags=self._base_tags)
        self.gauge("jobs.returned", len(statuses), tags=self._base_tags)

        now = time.time()
        finalized_changed = self._prune_state_map(self._finalized_runs, now, self._finalized_ttl_seconds)
        active_changed = self._prune_state_map(self._active_runs, now, self._active_ttl_seconds)

        if not statuses:
            if finalized_changed:
                self._persist_finalized_runs_cache()
            if active_changed:
                self._persist_active_runs_cache()
            return

        status_counts = {}
        active_by_server = {}
        waiting_by_server = {}

        for job in statuses:
            if not isinstance(job, dict):
                continue

            normalized_status = self._normalize_status(job.get("status"))
            ctm_server = str(job.get("ctm") or job.get("server") or "unknown")

            self._increment_count(status_counts, (ctm_server, normalized_status))
            if normalized_status not in _TERMINAL_STATUSES:
                self._increment_count(active_by_server, ctm_server)
            if normalized_status in _WAITING_STATUSES:
                self._increment_count(waiting_by_server, ctm_server)

            dedupe_key = self._build_run_key(job)

            if normalized_status in _TERMINAL_STATUSES:
                if self._handle_terminal_job(job, normalized_status, dedupe_key, now, ctm_server):
                    finalized_changed = True
                if dedupe_key is not None and dedupe_key in self._active_runs:
                    self._active_runs.pop(dedupe_key)
                    active_changed = True
            elif dedupe_key is not None:
                if dedupe_key not in self._active_runs:
                    active_changed = True
                self._active_runs[dedupe_key] = now

        for (ctm_server, normalized_status), count in status_counts.items():
            tags = self._base_tags + [f"ctm_server:{ctm_server}", f"status:{normalized_status}"]
            self.gauge("jobs.by_status", count, tags=tags)

        for ctm_server, count in active_by_server.items():
            tags = self._base_tags + [f"ctm_server:{ctm_server}"]
            self.gauge("jobs.active", count, tags=tags)

        global_waiting_total = sum(waiting_by_server.values())
        self.gauge("jobs.waiting.total", global_waiting_total, tags=self._base_tags)
        for ctm_server, count in waiting_by_server.items():
            tags = self._base_tags + [f"ctm_server:{ctm_server}"]
            self.gauge("jobs.waiting.total", count, tags=tags)

        if finalized_changed:
            self._persist_finalized_runs_cache()
        if active_changed:
            self._persist_active_runs_cache()

    def _handle_terminal_job(
        self, job: dict[str, Any], normalized_status: str, dedupe_key: str | None, now: float, ctm_server: str
    ) -> bool:
        if dedupe_key is None:
            self.log.debug("Skipping completion metrics for job without dedupe key: %s", job.get("name"))
            return False
        if dedupe_key in self._finalized_runs:
            return False

        result = self._result_from_status(normalized_status)
        metric_tags = self._job_metric_tags(job, ctm_server=ctm_server)
        completion_tags = metric_tags + [f"result:{result}"]
        self.count("job.run.count", 1, tags=completion_tags)

        duration_ms = self._duration_ms(job)
        if duration_ms is not None:
            self.histogram("job.run.duration_ms", duration_ms, tags=completion_tags)

        self._finalized_runs[dedupe_key] = now
        return True

    def _build_run_key(self, job: dict[str, Any]) -> str | None:
        job_id = job.get("jobId")
        if not job_id:
            return None

        number_of_runs = job.get("numberOfRuns")
        if number_of_runs is not None:
            return f"{job_id}#{number_of_runs}"

        start_time = self._timestamp_string(job.get("startTime"))
        if start_time:
            return f"{job_id}#{start_time}"

        end_time = self._timestamp_string(job.get("endTime"))
        if end_time:
            return f"{job_id}#{end_time}"

        return None

    def _prune_state_map(self, state_map: dict[str, float], now: float, ttl_seconds: int) -> bool:
        stale = [key for key, seen_at in state_map.items() if now - seen_at > ttl_seconds]
        for key in stale:
            state_map.pop(key)
        return bool(stale)

    def _load_finalized_runs_cache(self) -> None:
        self._finalized_runs = self._load_cache(_FINALIZED_RUNS_CACHE_KEY, self._finalized_ttl_seconds)

    def _persist_finalized_runs_cache(self) -> None:
        self._persist_cache(_FINALIZED_RUNS_CACHE_KEY, self._finalized_runs)

    def _load_active_runs_cache(self) -> None:
        self._active_runs = self._load_cache(_ACTIVE_RUNS_CACHE_KEY, self._active_ttl_seconds)

    def _persist_active_runs_cache(self) -> None:
        self._persist_cache(_ACTIVE_RUNS_CACHE_KEY, self._active_runs)

    def _load_cache(self, cache_key: str, ttl_seconds: int) -> dict[str, float]:
        raw = self.read_persistent_cache(cache_key)
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            self.log.warning("Could not decode persistent cache for %s; starting empty", cache_key)
            return {}
        if not isinstance(data, dict):
            self.log.warning("Persistent cache for %s is not a dict; starting empty", cache_key)
            return {}

        now = time.time()
        loaded = {}
        for key, value in data.items():
            if not isinstance(key, str):
                continue
            try:
                seen_at = float(value)
            except (TypeError, ValueError):
                continue
            if now - seen_at <= ttl_seconds:
                loaded[key] = seen_at

        self.log.debug("Loaded %d entries from persistent cache %s", len(loaded), cache_key)
        return loaded

    def _persist_cache(self, cache_key: str, state_map: dict[str, float]) -> None:
        try:
            self.write_persistent_cache(cache_key, json.dumps(state_map))
        except Exception as e:
            self.log.warning("Could not persist cache %s: %s", cache_key, e)

    def _increment_count(self, counter: dict, key: object) -> None:
        counter[key] = counter.get(key, 0) + 1

    def _normalize_status(self, status: Any) -> str:
        if not status:
            return "unknown"
        return _STATUS_NORMALIZATION.get(str(status).strip().lower(), "unknown")

    def _result_from_status(self, status: str) -> str:
        # Map the normalized status to a known result after job run completion.
        if status == "ended_ok":
            return "ok"
        if status == "ended_not_ok":
            return "failed"
        if status == "canceled":
            return "canceled"
        return "unknown"

    def _job_metric_tags(self, job: dict[str, Any], ctm_server: str | None = None) -> list[str]:
        if ctm_server is None:
            ctm_server = str(job.get("ctm") or job.get("server") or "unknown")
        tags = self._base_tags + [f"ctm_server:{ctm_server}"]

        job_name = job.get("name")
        if job_name:
            tags.append(f"job_name:{job_name}")

        folder = job.get("folder")
        if folder:
            tags.append(f"folder:{folder}")

        job_type = job.get("type")
        if job_type:
            tags.append(f"type:{str(job_type).lower()}")

        return tags

    def _duration_ms(self, job: dict[str, Any]) -> int | None:
        # Calculate the job duration in milliseconds from start/end timestamps.
        start = self._parse_datetime(job.get("startTime"))
        end = self._parse_datetime(job.get("endTime"))
        if start is None or end is None:
            return None
        delta_ms = int((end - start).total_seconds() * 1000)
        if delta_ms < 0:
            return None
        return delta_ms

    def _parse_datetime(self, value: Any) -> datetime | None:
        # Parse datetime values from compact Control-M format or human-readable fallback.
        timestamp = self._timestamp_string(value)
        if not timestamp:
            return None

        compact = timestamp.strip()
        if compact.isdigit() and len(compact) == 14:
            try:
                return datetime.strptime(compact, "%Y%m%d%H%M%S")
            except ValueError:
                return None

        try:
            return datetime.strptime(compact, "%b %d, %Y, %I:%M:%S %p")
        except ValueError:
            return None

    def _timestamp_string(self, value: Any) -> str | None:
        # Estimated times can sometimes be a list...
        if isinstance(value, list):
            if not value:
                return None
            first = value[0]
            if first is None:
                return None
            return str(first)

        if value is None:
            return None

        return str(value)

    @AgentCheck.metadata_entrypoint
    def _collect_metadata(self, servers: Any) -> None:
        # The /config/servers response is a list of server objects, each with
        # a "version" field (e.g. "9.0.21.080").  Report the first one found.
        if isinstance(servers, list):
            for server in servers:
                version = server.get("version")
                if version:
                    self.set_metadata("version", version)
                    self.log.debug("Collected Control-M version: %s", version)
                    return
        self.log.debug("Could not determine Control-M version from /config/servers response")
