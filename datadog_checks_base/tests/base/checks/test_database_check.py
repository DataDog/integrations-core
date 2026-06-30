# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.stubs.datadog_agent import datadog_agent


class FakeDatabaseCheck(DatabaseCheck):
    @property
    def reported_hostname(self):
        return None

    @property
    def dbms_version(self):
        return "1.0.0"

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


@pytest.mark.parametrize(
    ("tags", "template", "connection_params", "expected"),
    [
        pytest.param([], "$resolved_hostname", {"resolved_hostname": "my-host"}, "my-host", id="connection_params"),
        pytest.param(["env:prod"], "$env", None, "prod", id="substitutes_tags"),
        # Tags are sorted before merging, so the result is deterministic regardless of input order.
        pytest.param(["team:b", "team:a"], "$team", None, "a,b", id="merges_duplicate_keys_sorted"),
        pytest.param(["host:tag-host"], "$host", {"host": "conn-host"}, "conn-host", id="connection_params_override"),
        # Tags without a ':' are not exposed as template variables.
        pytest.param(["keyless"], "$keyless", None, "$keyless", id="ignores_keyless_tags"),
        pytest.param([], "$missing", None, "$missing", id="unknown_variables_intact"),
    ],
)
def test_build_database_identifier(tags, template, connection_params, expected):
    check = FakeDatabaseCheck("test", {}, [{}])
    check.tag_manager.set_tags_from_list(tags)
    assert check._build_database_identifier(template, connection_params) == expected


@pytest.mark.parametrize(
    ("template", "params", "tags", "tags_after", "expected"),
    [
        # template=None / params=None delegate to the base hooks (default template "$resolved_hostname").
        pytest.param(None, None, ["resolved_hostname:my-host"], None, "my-host", id="default_template_uses_tags"),
        # Non-string param values are stringified by the template engine, so no casting is needed.
        pytest.param("$host:$port", {"host": "db-host", "port": 5432}, [], None, "db-host:5432", id="overridden_hooks"),
        # Connection params take precedence over tags of the same name.
        pytest.param(
            "$host:$port",
            {"host": "db-host", "port": 5432},
            ["host:tag-host", "port:1111"],
            None,
            "db-host:5432",
            id="params_override_tags",
        ),
        # Mutating tags after first access has no effect: the identifier is built once and cached.
        pytest.param(
            None, None, ["resolved_hostname:first"], ["resolved_hostname:second"], "first", id="built_once_and_cached"
        ),
    ],
)
def test_database_identifier(template, params, tags, tags_after, expected):
    class EmbeddedDatabaseCheck(FakeDatabaseCheck):
        @property
        def database_identifier_template(self):
            return super().database_identifier_template if template is None else template

        @property
        def database_identifier_params(self):
            return super().database_identifier_params if params is None else params

    check = EmbeddedDatabaseCheck("test", {}, [{}])
    check.tag_manager.set_tags_from_list(tags)
    assert check.database_identifier == expected
    if tags_after is not None:
        check.tag_manager.set_tags_from_list(tags_after, replace=True)
        assert check.database_identifier == expected
