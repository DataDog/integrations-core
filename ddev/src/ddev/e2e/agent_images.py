# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Agent Docker images to run E2E tests against, selected by Python version and platform.

The Agent embeds its own Python, so an E2E run is only meaningful against an Agent whose embedded
Python matches the one the environment tests under. This module owns that mapping.
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
# free-threaded `3.13t`, an interpreter path) is rejected rather than guessed at.
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


# Each Agent release line embeds one Python version, recorded in datadog-agent's
# `omnibus/config/software/python3.rb`. Superseded lines are pinned to their last release, the
# current one tracks the dev build. When a new line bumps its Python, pin the outgoing one to its
# final release and point the new version at the dev images.
# There is no 3.10 entry because the Agent went from 3.9 straight to 3.11.
#
# These are base tags. `-jmx` is absent by design: whether an environment needs it is runtime
# metadata (`use_jmx`), and `ddev.e2e.agent.docker` appends the suffix itself.
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

    Pure and offline, so the same inputs always plan the same image.
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

    An explicit preflight, kept out of `get_agent_image` so planning stays offline. Each distinct
    image is queried once, and registry errors other than a missing manifest propagate rather than
    being reported as an absent image.
    """
    from ddev.utils.docker_registry import manifest_exists

    missing: list[str] = []
    for image in dict.fromkeys(images):
        host, repository, tag = parse_image_reference(image)
        if not manifest_exists(repository, tag, host=host):
            missing.append(image)

    return missing
