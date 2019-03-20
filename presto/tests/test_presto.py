# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


# We don't test JMXFetch based integrations in this repo
# This is required to allow E2E to spin up the environment
@pytest.mark.usefixtures('dd_environment')
def test():
    pass
