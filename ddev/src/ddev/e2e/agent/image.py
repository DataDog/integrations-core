# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re

AGENT_IMAGE_REGEX = r'^([^/]+)/([^:]+):(.*)$'
AGENT_VERSION_REGEX = (
    # Main version: 7, 7.69, 7.69.0 ...
    r"^(?P<version>\d+(?:\.[\dx]+)*|latest|main|master|nightly)"
    # rcs: rc.1, rc ...
    r"(?P<rc>-rc(?:\.\d+)?)?"
    # Any suffixes: -jmx, -linux, -full...
    r"(?P<suffixes>(?:-[a-zA-Z0-9]+)*)$"
)


def normalize_agent_image_name(agent_build: str | None, python_major: int, use_jmx: bool) -> str:
    agent_build = 'datadog/agent-dev:sarah-parser-go-client-py3'
    if use_jmx:
        agent_build += '-jmx'

    if match := re.match(AGENT_IMAGE_REGEX, agent_build):
        org, image, tag = match.groups()

        if org not in {'datadog', 'registry.datadoghq.com'}:
            # Some non-Datadog image has been selected.
            return agent_build

        version_match = re.match(AGENT_VERSION_REGEX, tag)
        if version_match is None:
            # The tag does not follow a recognized Agent version format.
            return agent_build

        version = version_match.group('version')
        rc = version_match.group('rc') or ''
        suffixes = version_match.group('suffixes')

        # Add a Python suffix when required by a development Agent image.
        if image == 'agent-dev':
            has_python_variant = any(suffix in suffixes for suffix in ('py', 'fips'))
            if not (rc or has_python_variant or version[0].isdigit()):
                suffixes = f'-py{python_major}{suffixes}'

        if use_jmx and '-jmx' not in suffixes:
            suffixes += '-jmx'

        return f'{org}/{image}:{version}{rc}{suffixes}'

    return agent_build
