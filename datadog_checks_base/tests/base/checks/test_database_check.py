# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures.thread import ThreadPoolExecutor
from unittest import mock

import pytest

from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.stubs.datadog_agent import datadog_agent
from datadog_checks.base.utils.db.utils import DBMAsyncJob


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


class RegistryTestJob(DBMAsyncJob):
    """Minimal DBMAsyncJob used to exercise the DatabaseCheck async job registry."""

    def __init__(self, check, enabled=True, job_name="test-job"):
        super().__init__(
            check,
            enabled=enabled,
            dbms="test-dbms",
            rate_limit=10,
            max_sleep_chunk_s=0.1,
            job_name=job_name,
        )
        self.shutdown_calls = 0

    def shutdown(self):
        self.shutdown_calls += 1

    def run_job(self):
        pass


@pytest.fixture
def registry_check():
    check = FakeDatabaseCheck("test", {}, [{}])
    yield check
    # Stop any registered jobs so their loops don't outlive the test.
    check.cancel_async_jobs()
    check.shutdown_async_jobs()


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # Recreate the shared executor per test so job loops don't leak across tests.
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


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


@pytest.mark.parametrize("register_twice", [False, True], ids=["single", "duplicate_instance"])
def test_register_async_job_adds_and_dedupes(registry_check, register_twice):
    job = RegistryTestJob(registry_check)
    assert registry_check.register_async_job(job) is job
    if register_twice:
        assert registry_check.register_async_job(job) is job
    assert registry_check._async_job_registry == {"test-job": job}


def test_register_async_job_replaces_job_with_same_name(registry_check):
    first = RegistryTestJob(registry_check, job_name="query-metrics")
    second = RegistryTestJob(registry_check, job_name="query-metrics")

    registry_check.register_async_job(first)
    registry_check.register_async_job(second)

    assert registry_check._async_job_registry == {"query-metrics": second}


def test_register_async_job_requires_job_name(registry_check):
    with pytest.raises(ValueError):
        registry_check.register_async_job(RegistryTestJob(registry_check, job_name=None))


@pytest.mark.parametrize("enabled", [True, False], ids=["enabled", "disabled"])
def test_run_async_jobs_starts_only_enabled_jobs(registry_check, enabled):
    job = registry_check.register_async_job(RegistryTestJob(registry_check, enabled=enabled))

    registry_check.run_async_jobs([])

    # Only enabled jobs get a running loop; disabled jobs are skipped by run_job_loop.
    assert (job._job_loop_future is not None) == enabled


def test_cancel_async_jobs_signals_without_touching_futures(registry_check):
    job = registry_check.register_async_job(RegistryTestJob(registry_check))
    registry_check.run_async_jobs([])
    assert job._job_loop_future is not None

    registry_check.cancel_async_jobs()

    # cancel_async_jobs only sets the cancel event; the future stays in place for shutdown to await.
    assert job._cancel_event.is_set()
    assert job._job_loop_future is not None


@pytest.mark.parametrize("started", [True, False], ids=["loop_started", "loop_not_started"])
def test_shutdown_async_jobs_tears_down_and_calls_shutdown(registry_check, started):
    job = registry_check.register_async_job(RegistryTestJob(registry_check))
    if started:
        registry_check.run_async_jobs([])
        assert job._job_loop_future is not None
        registry_check.cancel_async_jobs()

    registry_check.shutdown_async_jobs()

    # The future is cleared and shutdown runs once, whether or not a loop was started.
    assert job._job_loop_future is None
    assert job.shutdown_calls == 1
