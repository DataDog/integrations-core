# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.e2e.agent.docker import _normalize_agent_image_name
from ddev.e2e.agent_images import (
    AGENT_IMAGES_BY_PYTHON,
    LINUX,
    WINDOWS,
    AgentImages,
    UnknownPythonVersion,
    UnsupportedAgentPlatform,
    get_agent_image,
)


@pytest.mark.parametrize("platform", [LINUX, WINDOWS])
def test_every_known_python_version_resolves_on_every_platform(platform):
    for python_version in AGENT_IMAGES_BY_PYTHON:
        assert get_agent_image(python_version, platform)


def test_linux_and_windows_images_differ():
    assert get_agent_image('3.13', LINUX) != get_agent_image('3.13', WINDOWS)


def test_current_line_tracks_the_development_build():
    assert get_agent_image('3.13', LINUX) == 'registry.datadoghq.com/agent-dev:master-py3'
    assert get_agent_image('3.13', WINDOWS) == 'registry.datadoghq.com/agent:7-rc-servercore'


@pytest.mark.parametrize(
    "python_version, expected",
    [
        pytest.param('3.12', 'registry.datadoghq.com/agent:7.71.1', id="last-of-3.12-line"),
        pytest.param('3.11', 'registry.datadoghq.com/agent:7.57.2', id="last-of-3.11-line"),
    ],
)
def test_superseded_lines_are_pinned_to_their_final_release(python_version, expected):
    assert get_agent_image(python_version, LINUX) == expected


def test_windows_images_use_the_servercore_variant():
    assert get_agent_image('3.12', WINDOWS) == 'registry.datadoghq.com/agent:7.71.1-servercore'


@pytest.mark.parametrize(
    "python_version",
    [
        pytest.param('3.10', id="no-agent-ever-embedded-it"),
        pytest.param('4.0', id="does-not-exist"),
    ],
)
def test_python_version_without_an_agent_is_rejected(python_version):
    with pytest.raises(UnknownPythonVersion, match="No Agent release embeds"):
        get_agent_image(python_version, LINUX)


@pytest.mark.parametrize(
    "python_version",
    [
        pytest.param('3', id="major-only"),
        pytest.param('3.13t', id="free-threaded"),
        pytest.param('3.13.7', id="patch-level"),
        pytest.param('/usr/bin/python3', id="interpreter-path"),
        pytest.param('', id="empty"),
    ],
)
def test_malformed_python_version_is_rejected_rather_than_guessed(python_version):
    with pytest.raises(UnknownPythonVersion, match="Invalid Python version"):
        get_agent_image(python_version, LINUX)


def test_unsupported_platform_is_rejected():
    with pytest.raises(UnsupportedAgentPlatform, match="macos"):
        get_agent_image('3.13', 'macos')


@pytest.mark.parametrize("platform", [LINUX, WINDOWS])
def test_images_survive_ddev_jmx_normalization(platform):
    """Every image must keep its identity when ddev appends the JMX suffix at E2E runtime.

    `DockerAgent` rewrites the image name for JMX environments, so a tag shape it does not
    recognize would silently be passed through or mangled instead of gaining `-jmx`.
    """
    for python_version in AGENT_IMAGES_BY_PYTHON:
        image = get_agent_image(python_version, platform)

        assert _normalize_agent_image_name(image, 3, False) == image
        assert _normalize_agent_image_name(image, 3, True) == f'{image}-jmx'


def test_for_platform_rejects_an_unknown_platform():
    images = AgentImages(linux='a', windows='b')

    with pytest.raises(UnsupportedAgentPlatform):
        images.for_platform('freebsd')


@pytest.mark.requires_ci
@pytest.mark.parametrize("platform", [LINUX, WINDOWS])
def test_every_image_is_published(platform):
    """Guard against a typo or a tag that has been removed from the registry."""
    from ddev.utils.docker_registry import manifest_exists

    for python_version in AGENT_IMAGES_BY_PYTHON:
        image = get_agent_image(python_version, platform)
        _, _, remainder = image.partition('/')
        repository, _, tag = remainder.partition(':')

        assert manifest_exists(repository, tag), f'{image} is not published'
