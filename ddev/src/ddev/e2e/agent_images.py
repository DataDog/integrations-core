# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Agent Docker images to run E2E tests against, selected by Python version and platform.

An integration's Hatch environment pins the Python version its tests run under. The Agent embeds
its own Python interpreter, so an E2E run is only meaningful against an Agent whose embedded
Python matches that version. This module owns that mapping and is the single place to change when
a new Agent release line ships a new Python.

`get_agent_image` is pure and offline, so a test plan built from the same inputs is always
identical. `find_unpublished_images` is the separate, explicitly-called check that the images a
plan resolved actually exist in the registry.

Images here are base tags. The ``-jmx`` variant is deliberately absent: whether an environment
needs the JMX image is a per-environment runtime fact (``use_jmx`` in the E2E metadata) rather
than something known at planning time, and
:func:`ddev.e2e.agent.docker._normalize_agent_image_name` already appends the suffix when needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ddev.utils.platform import PlatformName

if TYPE_CHECKING:
    from collections.abc import Iterable

REGISTRY = 'registry.datadoghq.com'

# Hatch reports an environment's Python as `major.minor`. Anything else (a bare major, a
# free-threaded `3.13t`, an interpreter path) is rejected rather than guessed at, because
# silently mapping it onto the wrong Agent would run E2E against a mismatched interpreter.
PYTHON_VERSION_PATTERN = re.compile(r'^\d+\.\d+$')

IMAGE_REFERENCE_PATTERN = re.compile(r'^(?P<host>[^/]+)/(?P<repository>.+):(?P<tag>[^:]+)$')


class UnknownPythonVersion(Exception):
    """Raised when no Agent release line embeds the requested Python version."""


class UnsupportedAgentPlatform(Exception):
    """Raised when no Agent Docker image is published for the requested platform."""


@dataclass(frozen=True)
class AgentImages:
    """The Linux and Windows Agent Docker images for one Agent release line."""

    linux: str
    windows: str

    def for_platform(self, platform: PlatformName) -> str:
        if platform is PlatformName.LINUX:
            return self.linux
        if platform is PlatformName.WINDOWS:
            return self.windows

        raise UnsupportedAgentPlatform(f'No Agent Docker image is published for platform {platform!r}')


def released_images(version: str) -> AgentImages:
    """Build the image pair for a published Agent release."""
    return AgentImages(linux=f'{REGISTRY}/agent:{version}', windows=f'{REGISTRY}/agent:{version}-servercore')


# The Agent embeds one Python version per release line, recorded in datadog-agent's
# `omnibus/config/software/python3.rb`. Superseded lines are pinned to their last release; the
# current line tracks the development build so E2E follows the Agent being built. When a new line
# bumps its Python, pin the outgoing one to its final release and point the new version at the dev
# images. No entry exists for 3.10 because the Agent went from 3.9 straight to 3.11.
AGENT_IMAGES_BY_PYTHON: dict[str, AgentImages] = {
    # 7.72 onwards
    '3.13': AgentImages(linux=f'{REGISTRY}/agent-dev:master-py3', windows=f'{REGISTRY}/agent:7-rc-servercore'),
    # 7.58 - 7.71
    '3.12': released_images('7.71.1'),
    # 7.51 - 7.57
    '3.11': released_images('7.57.2'),
    # 7.47 - 7.50
    '3.9': released_images('7.50.3'),
    # 7.38 - 7.46
    '3.8': released_images('7.46.0'),
}


def get_agent_image(python_version: str, platform: PlatformName) -> str:
    """Return the Agent Docker image to run E2E tests for `python_version` on `platform`.

    `python_version` is a `major.minor` string as reported by Hatch (for example ``3.13``). Raises
    :class:`UnknownPythonVersion` when no Agent line embeds that Python and
    :class:`UnsupportedAgentPlatform` when the line publishes no image for that platform.
    """
    if not PYTHON_VERSION_PATTERN.match(python_version):
        raise UnknownPythonVersion(
            f'Invalid Python version {python_version!r}; expected a `major.minor` version such as `3.13`'
        )

    images = AGENT_IMAGES_BY_PYTHON.get(python_version)
    if images is None:
        supported = ', '.join(sorted(AGENT_IMAGES_BY_PYTHON))
        raise UnknownPythonVersion(f'No Agent release embeds Python {python_version}; known versions: {supported}')

    return images.for_platform(platform)


def parse_image_reference(image: str) -> tuple[str, str, str]:
    """Split a fully qualified image into its registry host, repository, and tag."""
    match = IMAGE_REFERENCE_PATTERN.match(image)
    if match is None:
        raise ValueError(f'Not a fully qualified `host/repository:tag` image reference: {image!r}')

    return match.group('host'), match.group('repository'), match.group('tag')


def find_unpublished_images(images: Iterable[str]) -> list[str]:
    """Return the given images that the registry does not serve, in first-seen order.

    Each distinct image is queried once. Callers use this as an explicit preflight so a bad or
    withdrawn tag surfaces before any job runs, instead of failing every E2E job in the plan.
    Registry errors other than a missing manifest propagate, so an unreachable registry is not
    mistaken for a missing image.
    """
    from ddev.utils.docker_registry import manifest_exists

    missing: list[str] = []
    for image in dict.fromkeys(images):
        host, repository, tag = parse_image_reference(image)
        if not manifest_exists(repository, tag, host=host):
            missing.append(image)

    return missing
