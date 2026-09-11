# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Generic resources pilot collector for ArgoCD."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

from datadog_checks.base.utils.http import RequestsWrapper

try:
    import datadog_agent
except ImportError:
    datadog_agent = None

from .resources_constants import (
    APPLICATION_INCLUDE,
    CLUSTER_INCLUDE,
    GENRESOURCES_API_UP_METRIC,
    GENRESOURCES_STREAM_UP_METRIC,
    KEY_SEPARATOR,
    PROJECT_INCLUDE,
    REPOSITORY_INCLUDE,
    URL_CREDENTIALS_PATTERN,
    auth_headers,
)
from .stream_listener import ArgocdApplicationStreamListener

if TYPE_CHECKING:
    from .check import ArgocdCheck


def _instance_prefix(endpoint: str | None) -> str:
    """Build a multi-part prefix that disambiguates resources across clusters and envs.

    Order: kube_cluster_name : env. The argocd hostname is used only as a
    last-resort fallback when neither cluster name nor env is available
    (e.g. an out-of-k8s agent monitoring a remote argocd without DD_ENV set).
    """
    parts: list[str] = []
    if datadog_agent is not None:
        cluster = ""
        try:
            cluster = datadog_agent.get_clustername() or ""
        except Exception:
            pass
        if not cluster:
            try:
                cluster = datadog_agent.get_config("cluster_name") or ""
            except Exception:
                pass
        if cluster:
            parts.append(cluster)
        try:
            tags = datadog_agent.get_config("tags") or []
        except Exception:
            tags = []
        env = next((t.split(":", 1)[1] for t in tags if t.startswith("env:")), "") or os.environ.get("DD_ENV", "")
        if env:
            parts.append(env)
    if not parts and endpoint:
        host = urlparse(endpoint).hostname or ""
        if host:
            parts.append(host)
    return KEY_SEPARATOR.join(parts)


@dataclass(frozen=True)
class ResourceTypeSpec:
    resource_type: str
    api_path: str
    include: dict[str, tuple[str, ...]]
    key_builder: Callable[[dict], str]


def _strip_url_userinfo(url: str) -> str:
    """Drop any embedded ``user:token@`` credentials from a URL."""
    parsed = urlparse(url)
    if not (parsed.username or parsed.password):
        return url
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


def _scrub_url_credentials(text: str) -> str:
    """Strip ``user:token@`` userinfo from any URL embedded in free text (e.g. error messages)."""
    return URL_CREDENTIALS_PATTERN.sub(r"\1", text)


def _scrub_repo_urls(container: dict) -> None:
    """Strip credentials from a source's repoURL and from any multi-source repoURLs, in place."""
    source = container.get("source")
    if isinstance(source, dict) and isinstance(source.get("repoURL"), str):
        source["repoURL"] = _strip_url_userinfo(source["repoURL"])
    for src in container.get("sources") or []:
        if isinstance(src, dict) and isinstance(src.get("repoURL"), str):
            src["repoURL"] = _strip_url_userinfo(src["repoURL"])


def _sanitize_item(item: dict, resource_type: str) -> None:
    """Strip embedded credentials from repo URLs and free-text messages in place before they ship."""
    if resource_type == "argocd_application":
        status = item.get("status") or {}
        _scrub_repo_urls(item.get("spec") or {})
        for entry in status.get("history") or []:
            if isinstance(entry, dict):
                _scrub_repo_urls(entry)
        operation_state = status.get("operationState")
        if isinstance(operation_state, dict) and isinstance(operation_state.get("message"), str):
            operation_state["message"] = _scrub_url_credentials(operation_state["message"])
        summary = status.get("summary") or {}
        external_urls = summary.get("externalURLs")
        if isinstance(external_urls, list):
            summary["externalURLs"] = [_strip_url_userinfo(u) if isinstance(u, str) else u for u in external_urls]
        for condition in status.get("conditions") or []:
            if isinstance(condition, dict) and isinstance(condition.get("message"), str):
                condition["message"] = _scrub_url_credentials(condition["message"])
    elif resource_type == "argocd_repository":
        if isinstance(item.get("repo"), str):
            item["repo"] = _strip_url_userinfo(item["repo"])
    elif resource_type == "argocd_project":
        spec = item.get("spec") or {}
        source_repos = spec.get("sourceRepos")
        if isinstance(source_repos, list):
            spec["sourceRepos"] = [_strip_url_userinfo(r) if isinstance(r, str) else r for r in source_repos]
    connection = item.get("connectionState")
    if isinstance(connection, dict) and isinstance(connection.get("message"), str):
        connection["message"] = _scrub_url_credentials(connection["message"])


def _change_token(item: dict) -> str:
    """A value that changes whenever the resource changes: k8s resourceVersion if present, else a content hash."""
    version = (item.get("metadata") or {}).get("resourceVersion")
    if isinstance(version, str) and version:
        return version
    encoded = json.dumps(item, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha1(encoded, usedforsecurity=False).hexdigest()


def _application_key(item: dict) -> str:
    metadata = item.get("metadata") or {}
    namespace = metadata.get("namespace") or "default"
    name = metadata.get("name")
    if not name:
        raise ValueError("argocd_application is missing metadata.name")
    return f"{namespace}{KEY_SEPARATOR}{name}"


def _cluster_key(item: dict) -> str:
    server = item.get("server")
    if not server:
        raise ValueError("argocd_cluster is missing server")
    return server


def _repository_key(item: dict) -> str:
    repo = item.get("repo")
    if not repo:
        raise ValueError("argocd_repository is missing repo")
    return repo


def _project_key(item: dict) -> str:
    metadata = item.get("metadata") or {}
    namespace = metadata.get("namespace") or "default"
    name = metadata.get("name")
    if not name:
        raise ValueError("argocd_project is missing metadata.name")
    return f"{namespace}{KEY_SEPARATOR}{name}"


RESOURCE_TYPE_SPECS: tuple[ResourceTypeSpec, ...] = (
    ResourceTypeSpec(
        resource_type="argocd_application",
        api_path="/api/v1/applications",
        include=APPLICATION_INCLUDE,
        key_builder=_application_key,
    ),
    ResourceTypeSpec(
        resource_type="argocd_cluster",
        api_path="/api/v1/clusters",
        include=CLUSTER_INCLUDE,
        key_builder=_cluster_key,
    ),
    ResourceTypeSpec(
        resource_type="argocd_repository",
        api_path="/api/v1/repositories",
        include=REPOSITORY_INCLUDE,
        key_builder=_repository_key,
    ),
    ResourceTypeSpec(
        resource_type="argocd_project",
        api_path="/api/v1/projects",
        include=PROJECT_INCLUDE,
        key_builder=_project_key,
    ),
)

APPLICATION_SPEC = next(spec for spec in RESOURCE_TYPE_SPECS if spec.resource_type == "argocd_application")
CLUSTER_SPEC = next(spec for spec in RESOURCE_TYPE_SPECS if spec.resource_type == "argocd_cluster")
REPOSITORY_SPEC = next(spec for spec in RESOURCE_TYPE_SPECS if spec.resource_type == "argocd_repository")
PROJECT_SPEC = next(spec for spec in RESOURCE_TYPE_SPECS if spec.resource_type == "argocd_project")


def _is_excluded(path: str, exclude_paths: tuple[str, ...]) -> bool:
    """True if a path equals an exclude entry or is nested beneath one (subtree match)."""
    return any(path == ex or path.startswith(f"{ex}.") or path.startswith(f"{ex}[") for ex in exclude_paths)


def _build_include(
    spec_include: dict[str, tuple[str, ...]], extra_paths: list[str], exclude_paths: tuple[str, ...]
) -> dict[str, list[str]]:
    """Compose a type's final allow-list: baseline paths plus extras, minus any excluded paths and maps."""
    paths = list(spec_include["paths"]) + extra_paths
    return {
        "paths": [p for p in paths if not _is_excluded(p, exclude_paths)],
        "map_paths": [p for p in spec_include["map_paths"] if not _is_excluded(p, exclude_paths)],
        "annotation_keys": list(spec_include["annotation_keys"]),
    }


class ArgocdResourceCollector:
    """Fetches ArgoCD Applications, Clusters, Repositories, and Projects and ships them as generic resources."""

    def __init__(self, check: "ArgocdCheck") -> None:
        self.check = check
        config = check.config
        self._endpoint: str | None = config.genresources_endpoint
        self._ttl_seconds: int = config.genresources_ttl_seconds
        self._max_resources: int = config.genresources_max_resources_per_cycle
        self._extra_paths: list[str] = list(config.genresources_extra_include_paths or [])
        self._exclude_paths: tuple[str, ...] = tuple(config.genresources_exclude_paths or [])
        self._auth_token: str | None = config.genresources_auth_token
        self._instance_prefix: str = _instance_prefix(self._endpoint)
        self._submitted: dict[str, str] = {}
        self._forgotten: dict[str, int] = {}
        self._stream_enabled: bool = bool(config.genresources_stream_applications_enabled)
        self._backoff_max: int = config.genresources_stream_backoff_max_seconds
        self._stream_read_timeout: int = config.genresources_stream_read_timeout_seconds
        self._app_poll_interval: int = config.genresources_application_poll_interval_seconds
        self._app_full_scrape_interval: int = config.genresources_application_full_scrape_interval_seconds
        self._cluster_scrape_interval: int = config.genresources_cluster_scrape_interval_seconds
        self._repository_scrape_interval: int = config.genresources_repository_scrape_interval_seconds
        self._collect_projects: bool = bool(config.genresources_collect_projects)
        self._project_scrape_interval: int = config.genresources_project_scrape_interval_seconds
        self._last_app_poll: float = 0.0
        self._last_app_full: float = 0.0
        self._last_cluster_scrape: float = 0.0
        self._last_repository_scrape: float = 0.0
        self._last_project_scrape: float = 0.0
        self._last_endpoint_warn: float = 0.0
        self._submitted_lock = threading.RLock()
        self._listener_lock = threading.Lock()
        self._stopped: bool = False
        self._listener: ArgocdApplicationStreamListener | None = None
        self._includes: dict[str, dict[str, list[str]]] = {
            spec.resource_type: _build_include(spec.include, self._extra_paths, self._exclude_paths)
            for spec in RESOURCE_TYPE_SPECS
        }
        for resource_type, include in self._includes.items():
            if not include["paths"] and not include["map_paths"]:
                self.check.log.warning(
                    "genresources: genresources_exclude_paths emptied the allow-list for %s; "
                    "nothing will be collected for it",
                    resource_type,
                )
        scrape_intervals = [
            self._app_full_scrape_interval,
            self._cluster_scrape_interval,
            self._repository_scrape_interval,
        ]
        if self._collect_projects:
            scrape_intervals.append(self._project_scrape_interval)
        longest_scrape_interval = max(scrape_intervals)
        if self._ttl_seconds < longest_scrape_interval:
            self.check.log.warning(
                "genresources: genresources_ttl_seconds (%d) is shorter than the longest scrape "
                "interval (%d); resources will expire before their next refresh and cause entity churn",
                self._ttl_seconds,
                longest_scrape_interval,
            )

    def collect(self) -> None:
        if not self._endpoint:
            self._report_endpoint_unavailable()
            return
        now = int(time.time())
        if self._stream_enabled:
            try:
                listener = self._ensure_listener()
            except Exception:
                self.check.log.exception("genresources: failed to start the application stream listener")
                listener = None
            connected = listener is not None and listener.is_connected()
            self.check.gauge(GENRESOURCES_STREAM_UP_METRIC, 1 if connected else 0)
        self._collect_due_types(now)

    def _report_endpoint_unavailable(self) -> None:
        """Throttle a misconfiguration warning and emit api.up=0 for every collected resource type."""
        now = int(time.time())
        if now - self._last_endpoint_warn >= self._app_poll_interval:
            self._last_endpoint_warn = now
            self.check.log.warning("collect_genresources is enabled but genresources_endpoint is not set; skipping")
        for spec in RESOURCE_TYPE_SPECS:
            if spec is PROJECT_SPEC and not self._collect_projects:
                continue
            self.check.gauge(GENRESOURCES_API_UP_METRIC, 0, tags=[f"resource_type:{spec.resource_type}"])

    def _collect_due_types(self, now: int) -> None:
        """Fetch each resource type when its own interval has elapsed (per-type cadences)."""
        expire_at = now + self._ttl_seconds
        # Applications: a full scrape (force_full) refreshes TTL and backfills; between full scrapes a
        # dedup poll catches changes when streaming is off (the stream covers that when it is on).
        if now - self._last_app_full >= self._app_full_scrape_interval:
            self._last_app_full = now
            self._last_app_poll = now
            self._collect_type(APPLICATION_SPEC, seen_at=now, expire_at=expire_at, force_full=True)
        elif not self._stream_enabled and now - self._last_app_poll >= self._app_poll_interval:
            self._last_app_poll = now
            self._collect_type(APPLICATION_SPEC, seen_at=now, expire_at=expire_at, force_full=False)
        # Clusters, Repositories, and Projects are always polled (never streamed); each scrape is a full re-submit.
        if now - self._last_cluster_scrape >= self._cluster_scrape_interval:
            self._last_cluster_scrape = now
            self._collect_type(CLUSTER_SPEC, seen_at=now, expire_at=expire_at, force_full=True)
        if now - self._last_repository_scrape >= self._repository_scrape_interval:
            self._last_repository_scrape = now
            self._collect_type(REPOSITORY_SPEC, seen_at=now, expire_at=expire_at, force_full=True)
        if self._collect_projects and now - self._last_project_scrape >= self._project_scrape_interval:
            self._last_project_scrape = now
            self._collect_type(PROJECT_SPEC, seen_at=now, expire_at=expire_at, force_full=True)

    def _ensure_listener(self) -> ArgocdApplicationStreamListener | None:
        with self._listener_lock:
            if self._stopped:
                return None
            if self._listener is None:
                self._listener = ArgocdApplicationStreamListener(
                    self.check,
                    self,
                    endpoint=self._endpoint,
                    auth_token=self._auth_token,
                    backoff_max_seconds=self._backoff_max,
                    read_timeout_seconds=self._stream_read_timeout,
                    http=RequestsWrapper(
                        self.check.instance,
                        self.check.init_config,
                        self.check.HTTP_CONFIG_REMAPPER,
                        self.check.log,
                    ),
                )
            if not self._listener.is_alive():
                self._listener.start()
            return self._listener

    def stop(self) -> None:
        """Signal the stream listener to stop; must not block, per AgentCheck.cancel()'s contract."""
        with self._listener_lock:
            self._stopped = True
            listener = self._listener
        if listener is not None:
            listener.cancel()

    def emit_stream_application(self, application: dict) -> None:
        """Emit a single application received from the stream (ADDED/MODIFIED) through the shared pipeline.

        Mutates ``application`` in place (credential sanitization); the caller must not reuse the dict after.
        """
        seen_at = int(time.time())
        self._emit_item(
            application, APPLICATION_SPEC, seen_at=seen_at, expire_at=seen_at + self._ttl_seconds, force_full=False
        )

    def forget_application(self, application: dict) -> None:
        """Drop a deleted application from the dedup cache so it stops refreshing and expires via TTL."""
        try:
            key = _application_key(application)
        except (ValueError, AttributeError):
            self.check.log.debug("genresources: skipping malformed DELETED application", exc_info=True)
            return
        cache_key = self._submitted_cache_key(APPLICATION_SPEC.resource_type, key)
        with self._submitted_lock:
            self._submitted.pop(cache_key, None)
            self._forgotten[cache_key] = int(time.time())

    def _prefixed(self, resource_key: str) -> str:
        """Prefix a resource key with the instance prefix (cluster|env) when one is configured."""
        if self._instance_prefix:
            return f"{self._instance_prefix}{KEY_SEPARATOR}{resource_key}"
        return resource_key

    def _submitted_cache_key(self, resource_type: str, resource_key: str) -> str:
        """Dedup-cache key for a resource: resource_type joined with the instance-prefixed key."""
        return f"{resource_type}{KEY_SEPARATOR}{self._prefixed(resource_key)}"

    def _collect_type(self, spec: ResourceTypeSpec, *, seen_at: int, expire_at: int, force_full: bool) -> None:
        tags = [f"resource_type:{spec.resource_type}"]
        try:
            items = self._fetch(spec.api_path)
        except Exception:
            self.check.log.exception("genresources: failed to fetch %s", spec.resource_type)
            self.check.gauge(GENRESOURCES_API_UP_METRIC, 0, tags=tags)
            return

        self.check.gauge(GENRESOURCES_API_UP_METRIC, 1, tags=tags)

        if len(items) > self._max_resources:
            self.check.log.warning(
                "genresources: volume cap hit for type=%s: fetched %d, capped at %d; "
                "increase genresources_max_resources_per_cycle if expected",
                spec.resource_type,
                len(items),
                self._max_resources,
            )
            items = items[: self._max_resources]

        seen = set()
        for item in items:
            cache_key = self._emit_item(item, spec, seen_at=seen_at, expire_at=expire_at, force_full=force_full)
            if cache_key is not None:
                seen.add(cache_key)
        # A stream frame that lands between _fetch above and this prune isn't in `seen`, so its fresh cache
        # entry is dropped here. Harmless: the app was already submitted; it just gets one redundant re-submit
        # on its next stream frame. Holding the lock across the fetch would stall real-time emits instead.
        namespace = f"{spec.resource_type}{KEY_SEPARATOR}"
        with self._submitted_lock:
            self._submitted = {k: v for k, v in self._submitted.items() if not k.startswith(namespace) or k in seen}
            # A tombstone only needs to outlive fetches that started before it; this scrape's seen_at is
            # older than any future scrape's, so a tombstone already <= it can't protect a later one.
            self._forgotten = {k: v for k, v in self._forgotten.items() if not k.startswith(namespace) or v > seen_at}

    def _fetch(self, api_path: str) -> list[dict]:
        url = self._endpoint.rstrip("/") + api_path
        # Pass a dedicated genresources token only when set, via extra_headers (merges with configured
        # headers). Omit it otherwise: even an empty extra_headers makes RequestsWrapper snapshot the default
        # headers before its auth_token handler writes the inherited token, which would drop that auth.
        kwargs: dict = {}
        headers = auth_headers(self._auth_token)
        if headers:
            kwargs["extra_headers"] = headers
        response = self.check.http.get(url, **kwargs)
        response.raise_for_status()
        payload = response.json()
        return list(payload.get("items") or [])

    def _emit_item(
        self, item: dict, spec: ResourceTypeSpec, *, seen_at: int, expire_at: int, force_full: bool
    ) -> str | None:
        try:
            token = _change_token(item)
        except Exception:
            self.check.log.warning("genresources: skipping malformed %s", spec.resource_type, exc_info=True)
            return None
        try:
            _sanitize_item(item, spec.resource_type)
        except Exception:
            self.check.log.exception("genresources: sanitize failed for %s", spec.resource_type)
            return None
        try:
            raw_key = spec.key_builder(item)
        except Exception:
            self.check.log.warning("genresources: skipping malformed %s", spec.resource_type, exc_info=True)
            return None
        key = self._prefixed(raw_key)
        include = self._includes[spec.resource_type]
        cache_key = self._submitted_cache_key(spec.resource_type, raw_key)
        with self._submitted_lock:
            if force_full and self._forgotten.get(cache_key, 0) >= seen_at:
                # This snapshot may predate a DELETED frame the listener already processed; don't let a
                # stale full-scrape resurrect what the stream correctly forgot.
                return None
            if force_full or self._submitted.get(cache_key) != token:
                try:
                    self.check.submit_generic_resource(
                        type=spec.resource_type,
                        key=key,
                        fields=item,
                        include=include,
                        seen_at=seen_at,
                        expire_at=expire_at,
                    )
                    self._submitted[cache_key] = token
                except Exception:
                    self.check.log.exception("genresources: failed to submit %s (key=%s)", spec.resource_type, key)
        return cache_key
