# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(autouse=True)
def configure_github_credentials(config_file):
    """Provide github credentials so commands that touch app.github do not abort."""
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
