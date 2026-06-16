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
        "status.conditions[*].type",
        "status.conditions[*].message",
        "status.conditions[*].lastTransitionTime",
        "status.operationState.phase",
        "status.operationState.startedAt",
        "status.operationState.finishedAt",
        "status.operationState.operation.initiatedBy.username",
        "status.operationState.operation.initiatedBy.automated",
        "status.sourceType",
        "status.reconciledAt",
        "status.summary.images[*]",
        "status.history[*].id",
        "status.history[*].revision",
        "status.history[*].deployedAt",
        "status.history[*].deployStartedAt",
        "status.history[*].initiatedBy.username",
        "status.history[*].initiatedBy.automated",
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

URL_CREDENTIALS_PATTERN = re.compile(r"([a-zA-Z][a-zA-Z0-9+.\-]*://)[^/\s@]+@")
