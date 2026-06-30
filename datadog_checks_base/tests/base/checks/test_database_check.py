# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.stubs.datadog_agent import datadog_agent


class FakeDatabaseCheck(DatabaseCheck):
    @property
    def reported_hostname(self):
        return None

    @property
    def database_identifier(self):
        return "test-db"

    @property
    def dbms_version(self):
        return "1.0.0"

    @property
    def tags(self):
        return []

    @property
    def cloud_metadata(self):
        return {}


def test_agent_hostname_resolves_once_and_caches():
    check = FakeDatabaseCheck("test", {}, [{}])
    # The hostname comes from an FFI call, so it should only be resolved once and cached.
    with mock.patch.object(datadog_agent, "get_hostname", return_value="my-agent-host") as get_hostname:
        assert check.agent_hostname == "my-agent-host"
        assert check.agent_hostname == "my-agent-host"
        assert get_hostname.call_count == 1
