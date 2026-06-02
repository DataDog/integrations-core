# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Generic resources pilot collector for ArgoCD."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable
from urllib.parse import urlparse, urlunparse

try:
    import datadog_agent
except ImportError:
    datadog_agent = None

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
    return ":".join(parts)


GENRESOURCES_API_UP_METRIC = "argocd.genresources.api.up"


@dataclass(frozen=True)
class ResourceTypeSpec:
    resource_type: str
    api_path: str
    include: dict[str, tuple[str, ...]]
    key_builder: Callable[[dict], str]


APPLICATION_INCLUDE: dict[str, tuple[str, ...]] = {
    "paths": (
        "metadata.name",
        "metadata.namespace",
        "spec.project",
        "spec.source.repoURL",
        "spec.source.path",
        "spec.source.targetRevision",
        "spec.source.chart",
        "spec.sources[*].repoURL",
        "spec.sources[*].path",
        "spec.sources[*].targetRevision",
        "spec.destination.server",
        "spec.destination.namespace",
        "spec.destination.name",
        "spec.syncPolicy.automated.prune",
        "spec.syncPolicy.automated.selfHeal",
        "status.sync.status",
        "status.sync.revision",
        "status.health.status",
        "status.health.message",
        "status.operationState.phase",
        "status.operationState.operation.initiatedBy.username",
        "status.sourceType",
        "status.reconciledAt",
        "status.resources[*].kind",
        "status.resources[*].name",
        "status.resources[*].namespace",
        "status.resources[*].status",
        "status.resources[*].health.status",
    ),
    "map_paths": ("metadata.labels",),
    "annotation_keys": (),
}

CLUSTER_INCLUDE: dict[str, tuple[str, ...]] = {
    "paths": (
        "name",
        "server",
        "serverVersion",
        "namespaces[*]",
        "connectionState.status",
        "connectionState.message",
        "info.applicationsCount",
        "info.serverVersion",
        "info.cacheInfo.resourcesCount",
    ),
    "map_paths": ("labels",),
    "annotation_keys": (),
}

REPOSITORY_INCLUDE: dict[str, tuple[str, ...]] = {
    "paths": (
        "repo",
        "type",
        "name",
        "project",
        "connectionState.status",
        "connectionState.message",
    ),
    "map_paths": (),
    "annotation_keys": (),
}


def _strip_url_userinfo(url: str) -> str:
    """Drop any embedded ``user:token@`` credentials from a URL."""
    parsed = urlparse(url)
    if not (parsed.username or parsed.password):
        return url
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


def _sanitize_repo_urls(item: dict, resource_type: str) -> None:
    """Strip embedded credentials from repo URLs in place before they ship or become keys."""
    if resource_type == "argocd_application":
        spec = item.get("spec") or {}
        source = spec.get("source")
        if isinstance(source, dict) and isinstance(source.get("repoURL"), str):
            source["repoURL"] = _strip_url_userinfo(source["repoURL"])
        for src in spec.get("sources") or []:
            if isinstance(src, dict) and isinstance(src.get("repoURL"), str):
                src["repoURL"] = _strip_url_userinfo(src["repoURL"])
    elif resource_type == "argocd_repository":
        if isinstance(item.get("repo"), str):
            item["repo"] = _strip_url_userinfo(item["repo"])


def _application_key(item: dict) -> str:
    metadata = item.get("metadata") or {}
    namespace = metadata.get("namespace") or "default"
    name = metadata.get("name")
    if not name:
        raise ValueError("argocd_application is missing metadata.name")
    return f"{namespace}:{name}"


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
)


class ArgocdResourceCollector:
    """Fetches ArgoCD Applications, Clusters, and Repositories and ships them as generic resources."""

    def __init__(self, check: "ArgocdCheck") -> None:
        self.check = check
        instance = check.instance
        self._endpoint: str | None = instance.get("generic_resources_endpoint")
        self._ttl_seconds: int = instance.get("genresources_ttl_seconds", 21600)
        self._max_resources: int = instance.get("max_resources_per_cycle", 10000)
        self._extra_paths: list[str] = list(instance.get("extra_include_paths") or [])
        self._auth_token: str | None = instance.get("generic_resources_auth_token")
        self._instance_prefix: str = _instance_prefix(self._endpoint)

    def collect(self) -> None:
        if not self._endpoint:
            self.check.log.warning(
                "collect_genresources is enabled but generic_resources_endpoint is not set; skipping"
            )
            for spec in RESOURCE_TYPE_SPECS:
                self.check.gauge(GENRESOURCES_API_UP_METRIC, 0, tags=[f"resource_type:{spec.resource_type}"])
            return

        seen_at = int(time.time())
        expire_at = seen_at + self._ttl_seconds

        for spec in RESOURCE_TYPE_SPECS:
            self._collect_type(spec, seen_at=seen_at, expire_at=expire_at)

    def _collect_type(self, spec: ResourceTypeSpec, *, seen_at: int, expire_at: int) -> None:
        tags = [f"resource_type:{spec.resource_type}"]
        try:
            items = self._fetch(spec.api_path)
        except Exception as exc:
            self.check.log.error("genresources: failed to fetch %s: %s", spec.resource_type, exc)
            self.check.gauge(GENRESOURCES_API_UP_METRIC, 0, tags=tags)
            return

        self.check.gauge(GENRESOURCES_API_UP_METRIC, 1, tags=tags)

        if len(items) > self._max_resources:
            self.check.log.warning(
                "genresources: volume cap hit (%d / %d) for type=%s; increase max_resources_per_cycle if expected",
                self._max_resources,
                len(items),
                spec.resource_type,
            )
            items = items[: self._max_resources]

        for item in items:
            self._emit_item(item, spec, seen_at=seen_at, expire_at=expire_at)

    def _fetch(self, api_path: str) -> list[dict]:
        url = self._endpoint.rstrip("/") + api_path
        kwargs: dict = {}
        if self._auth_token:
            kwargs["headers"] = {"Authorization": f"Bearer {self._auth_token}"}
        response = self.check.http.get(url, **kwargs)
        response.raise_for_status()
        payload = response.json()
        return list(payload.get("items") or [])

    def _emit_item(self, item: dict, spec: ResourceTypeSpec, *, seen_at: int, expire_at: int) -> None:
        try:
            _sanitize_repo_urls(item, spec.resource_type)
            key = spec.key_builder(item)
        except Exception:
            self.check.log.warning("genresources: skipping malformed %s", spec.resource_type, exc_info=True)
            return
        if self._instance_prefix:
            key = f"{self._instance_prefix}:{key}"
        try:
            self.check.submit_generic_resource(
                type=spec.resource_type,
                key=key,
                fields=item,
                include={
                    "paths": list(spec.include["paths"]) + self._extra_paths,
                    "map_paths": list(spec.include["map_paths"]),
                    "annotation_keys": list(spec.include["annotation_keys"]),
                },
                seen_at=seen_at,
                expire_at=expire_at,
            )
        except Exception:
            self.check.log.exception("genresources: failed to submit %s (key=%s)", spec.resource_type, key)
