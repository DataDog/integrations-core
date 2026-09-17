# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from ddev.config.file import ConfigFileWithOverrides


@pytest.fixture(autouse=True)
def configure_github_credentials(config_file: ConfigFileWithOverrides) -> None:
    """Provide github credentials so commands that touch app.github do not abort."""
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()


@pytest.fixture
def httpx_at_debug() -> Generator[logging.Logger, None, None]:
    """Force the httpx logger to DEBUG and restore its previous level on teardown."""
    logger = logging.getLogger('httpx')
    previous_level = logger.level
    logger.setLevel(logging.DEBUG)
    try:
        yield logger
    finally:
        logger.setLevel(previous_level)
