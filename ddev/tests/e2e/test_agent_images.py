# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.e2e.agent.image import normalize_agent_image_name
from ddev.e2e.agent_images import (
    AGENT_IMAGES_BY_PYTHON,
    UnknownPythonVersion,
    UnsupportedAgentPlatform,
    find_unpublished_images,
    get_agent_image,
    parse_image_reference,
)
from ddev.utils.platform import PlatformName


@pytest.mark.parametrize(
    ("python_version", "platform", "expected"),
    [
        pytest.param('3.13', PlatformName.LINUX, 'registry.datadoghq.com/agent-dev:master-py3', id="current-dev"),
        pytest.param('3.13', PlatformName.WINDOWS, 'registry.datadoghq.com/agent:7-rc-servercore', id="current-rc"),
        pytest.param('3.12', PlatformName.LINUX, 'registry.datadoghq.com/agent:7.71.1', id="last-of-3.12-line"),
        pytest.param(
            '3.12', PlatformName.WINDOWS, 'registry.datadoghq.com/agent:7.71.1-servercore', id="servercore-variant"
        ),
        pytest.param('3.11', PlatformName.LINUX, 'registry.datadoghq.com/agent:7.57.2', id="last-of-3.11-line"),
    ],
)
def test_agent_image_for_release_line(python_version, platform, expected):
    assert get_agent_image(python_version, platform) == expected


@pytest.mark.parametrize(
    "python_version",
    [
        pytest.param('3.10', id="no-agent-ever-embedded-it"),
        pytest.param('4.0', id="does-not-exist"),
    ],
)
def test_python_version_without_an_agent_is_rejected(python_version):
    with pytest.raises(UnknownPythonVersion, match="No Agent release embeds"):
        get_agent_image(python_version, PlatformName.LINUX)


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
        get_agent_image(python_version, PlatformName.LINUX)


def test_unsupported_platform_is_rejected():
    with pytest.raises(UnsupportedAgentPlatform, match="macos"):
        get_agent_image('3.13', PlatformName.MACOS)


@pytest.mark.parametrize("platform", [PlatformName.LINUX, PlatformName.WINDOWS])
def test_images_survive_ddev_jmx_normalization(platform):
    """Every image must keep its identity when ddev appends the JMX suffix at E2E runtime.

    `DockerAgent` rewrites the image name for JMX environments, so a tag shape it does not
    recognize would silently be passed through or mangled instead of gaining `-jmx`.
    """
    for python_version in AGENT_IMAGES_BY_PYTHON:
        image = get_agent_image(python_version, platform)

        assert normalize_agent_image_name(image, 3, False) == image
        assert normalize_agent_image_name(image, 3, True) == f'{image}-jmx'


@pytest.mark.parametrize(
    "image, expected",
    [
        pytest.param(
            'registry.datadoghq.com/agent:7.71.1-servercore',
            ('registry.datadoghq.com', 'agent', '7.71.1-servercore'),
            id="release",
        ),
        pytest.param(
            'registry.datadoghq.com/agent-dev:master-py3',
            ('registry.datadoghq.com', 'agent-dev', 'master-py3'),
            id="dev",
        ),
        pytest.param('host/nested/repository:tag', ('host', 'nested/repository', 'tag'), id="nested-repository"),
    ],
)
def test_parse_image_reference(image, expected):
    assert parse_image_reference(image) == expected


@pytest.mark.parametrize("image", ['agent:7.71.1', 'registry.datadoghq.com/agent', ''])
def test_parse_image_reference_rejects_an_incomplete_reference(image):
    with pytest.raises(ValueError, match="fully qualified"):
        parse_image_reference(image)


def test_find_unpublished_images_queries_each_distinct_image_once(monkeypatch):
    queried: list[tuple[str, str]] = []

    def fake_manifest_exists(repository, tag, *, host, **kwargs):
        queried.append((repository, tag))
        return tag != 'gone'

    monkeypatch.setattr('ddev.utils.docker_registry.manifest_exists', fake_manifest_exists)

    missing = find_unpublished_images(
        ['host/agent:here', 'host/agent:gone', 'host/agent:here'],
    )

    assert missing == ['host/agent:gone']
    assert queried == [('agent', 'here'), ('agent', 'gone')]


def test_find_unpublished_images_propagates_a_registry_failure(monkeypatch):
    # An unreachable registry must not be reported as a missing image, or a network blip would
    # look like a withdrawn tag.
    def failing_manifest_exists(repository, tag, *, host, **kwargs):
        raise OSError("registry unreachable")

    monkeypatch.setattr('ddev.utils.docker_registry.manifest_exists', failing_manifest_exists)

    with pytest.raises(OSError, match="registry unreachable"):
        find_unpublished_images(['host/agent:here'])


@pytest.mark.requires_ci
def test_every_image_in_the_manifest_is_published():
    """Guard against a typo or a tag that has been withdrawn from the registry."""
    images = [
        get_agent_image(python_version, platform)
        for python_version in AGENT_IMAGES_BY_PYTHON
        for platform in (PlatformName.LINUX, PlatformName.WINDOWS)
    ]

    assert find_unpublished_images(images) == []
