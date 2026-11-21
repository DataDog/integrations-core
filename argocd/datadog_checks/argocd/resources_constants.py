# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Constants for the ArgoCD generic resources collector."""

from __future__ import annotations

import re

# Resource-key delimiter. "|" rather than ":" because ":" appears inside cluster/repo server URLs
# (https://host:port). "|" can't occur in a k8s name/namespace, hostname, URL, or DD tag value, so keys
# stay unambiguously splittable.
KEY_SEPARATOR = "|"

GENRESOURCES_API_UP_METRIC = "argocd.genresources.api.up"
GENRESOURCES_STREAM_UP_METRIC = "argocd.genresources.stream.up"
GENRESOURCES_STREAM_EVENTS_METRIC = "argocd.genresources.stream.events_received"
GENRESOURCES_STREAM_RECONNECTS_METRIC = "argocd.genresources.stream.reconnects"


def auth_headers(token: str | None) -> dict[str, str]:
    """Bearer auth header for Argo CD API requests, or empty when no token is configured."""
    return {"Authorization": f"Bearer {token}"} if token else {}


APPLICATION_INCLUDE: dict[str, tuple[str, ...]] = {
    "paths": (
        "metadata.name",
        "metadata.namespace",
        "metadata.uid",
        "metadata.creationTimestamp",
        "spec.project",
        "spec.source.repoURL",
        "spec.source.path",
        "spec.source.targetRevision",
        "spec.source.chart",
        "spec.sources[*].repoURL",
        "spec.sources[*].path",
        "spec.sources[*].targetRevision",
        "spec.sources[*].chart",
        "spec.destination.server",
        "spec.destination.namespace",
        "spec.destination.name",
        "spec.syncPolicy.automated.prune",
        "spec.syncPolicy.automated.selfHeal",
        "status.sync.status",
        "status.sync.revision",
        "status.health.status",
        "status.health.message",
        "status.health.lastTransitionTime",
        "status.conditions[*].type",
        "status.conditions[*].message",
        "status.conditions[*].lastTransitionTime",
        "status.operationState.phase",
        "status.operationState.startedAt",
        "status.operationState.finishedAt",
        "status.operationState.message",
        "status.operationState.retryCount",
        "status.operationState.operation.initiatedBy.username",
        "status.operationState.operation.initiatedBy.automated",
        "status.sourceType",
        "status.reconciledAt",
        "status.summary.images[*]",
        "status.summary.externalURLs[*]",
        "status.history[*].id",
        "status.history[*].revision",
        "status.history[*].deployedAt",
        "status.history[*].deployStartedAt",
        "status.history[*].initiatedBy.username",
        "status.history[*].initiatedBy.automated",
        "status.history[*].source.repoURL",
        "status.history[*].source.path",
        "status.history[*].source.targetRevision",
        "status.history[*].source.chart",
        "status.history[*].sources[*].repoURL",
        "status.history[*].sources[*].path",
        "status.history[*].sources[*].targetRevision",
        "status.history[*].sources[*].chart",
        "status.history[*].revisions[*]",
        "status.resources[*].kind",
        "status.resources[*].name",
        "status.resources[*].namespace",
        "status.resources[*].group",
        "status.resources[*].version",
        "status.resources[*].status",
        "status.resources[*].health.status",
        "status.resources[*].requiresPruning",
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
        "connectionState.attemptedAt",
        "info.applicationsCount",
        "info.serverVersion",
        "info.cacheInfo.resourcesCount",
        "info.connectionState.status",
        "shard",
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
        "connectionState.attemptedAt",
        "insecure",
        "enableLfs",
        "enableOCI",
        "forceHttpBasicAuth",
    ),
    "map_paths": (),
    "annotation_keys": (),
}

PROJECT_INCLUDE: dict[str, tuple[str, ...]] = {
    "paths": (
        "metadata.name",
        "metadata.namespace",
        "metadata.uid",
        "metadata.creationTimestamp",
        "spec.description",
        "spec.sourceRepos[*]",
        "spec.destinations[*].server",
        "spec.destinations[*].namespace",
        "spec.destinations[*].name",
        "spec.namespaceResourceWhitelist[*].group",
        "spec.namespaceResourceWhitelist[*].kind",
        "spec.namespaceResourceBlacklist[*].group",
        "spec.namespaceResourceBlacklist[*].kind",
        "spec.clusterResourceWhitelist[*].group",
        "spec.clusterResourceWhitelist[*].kind",
        "spec.clusterResourceBlacklist[*].group",
        "spec.clusterResourceBlacklist[*].kind",
        "spec.permitOnlyProjectScopedClusters",
        "spec.roles[*].name",
        "spec.roles[*].description",
        "spec.roles[*].policies[*]",
        "spec.syncWindows[*].kind",
        "spec.syncWindows[*].schedule",
        "spec.syncWindows[*].duration",
        "spec.syncWindows[*].manualSync",
        "spec.syncWindows[*].timeZone",
        "spec.syncWindows[*].applications[*]",
        "spec.syncWindows[*].namespaces[*]",
        "spec.syncWindows[*].clusters[*]",
    ),
    "map_paths": ("metadata.labels", "metadata.annotations"),
    "annotation_keys": (),
}

URL_CREDENTIALS_PATTERN = re.compile(r"([a-zA-Z][a-zA-Z0-9+.\-]*://)[^/\s@]+@")
