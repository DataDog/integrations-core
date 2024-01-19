# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def test_check(dd_agent_check):
    dd_agent_check(rate=True)
