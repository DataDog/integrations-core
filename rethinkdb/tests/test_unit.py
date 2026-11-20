# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime as dt

import mock
import pytest

import rethinkdb
from datadog_checks.base import ConfigurationError
from datadog_checks.base.utils.time import UTC
from datadog_checks.rethinkdb import RethinkDBCheck, queries_impl
from datadog_checks.rethinkdb.config import Config
from datadog_checks.rethinkdb.queries import DatabaseTableMetrics
from datadog_checks.rethinkdb.types import Instance  # noqa: F401
from datadog_checks.rethinkdb.utils import to_time_elapsed
from datadog_checks.rethinkdb.version import parse_version

from .common import MALFORMED_VERSION_STRING_PARAMS

pytestmark = pytest.mark.unit


# --- config.py ---


def test_default_config():
    config = Config()
    assert config.host == "localhost"
    assert config.port == 28015
    assert config.user is None
    assert config.password is None
    assert config.tls_ca_cert is None
    assert config.tags == []
    assert config.service_check_tags == ("host:localhost", "port:28015")


def test_config_with_all_fields():
    instance = {
        "host": "192.168.121.1",
        "port": "28016",
        "username": "datadog-agent",
        "password": "s3kr3t",
        "tls_ca_cert": "/path/to/client.cert",
        "tags": ["rethinkdb_env:testing"],
    }  # type: Instance
    config = Config(instance)
    assert config.host == "192.168.121.1"
    assert config.port == 28016
    assert config.user == "datadog-agent"
    assert config.password == "s3kr3t"
    assert config.tls_ca_cert == "/path/to/client.cert"
    assert config.tags == ["rethinkdb_env:testing"]
    assert config.service_check_tags == ("host:192.168.121.1", "port:28016", "rethinkdb_env:testing")


@pytest.mark.parametrize("value", [42, True, object()])
def test_invalid_host(value):
    with pytest.raises(ConfigurationError):
        Config(instance={"host": value})


@pytest.mark.parametrize("value", ["280.16", "true", object()])
def test_invalid_port_not_convertible_to_int(value):
    with pytest.raises(ConfigurationError):
        Config(instance={"port": value})


def test_port_zero_is_valid():
    assert Config(instance={"port": 0}).port == 0


def test_negative_port_is_invalid():
    with pytest.raises(ConfigurationError):
        Config(instance={"port": -1})


def test_invalid_tags():
    with pytest.raises(ConfigurationError):
        Config(instance={"tags": "not-a-list"})


# --- utils.py ---


def test_to_time_elapsed():
    one_day_seconds = 3600 * 24
    assert to_time_elapsed(dt.datetime.now(UTC) - dt.timedelta(days=1)) == pytest.approx(one_day_seconds, abs=1)


# --- version.py ---


@pytest.mark.parametrize(
    "version_string, expected_version",
    [
        pytest.param("rethinkdb 2.4.0~0bionic (CLANG 6.0.0 (tags/RELEASE_600/final))", "2.4.0", id="2.4"),
        pytest.param("rethinkdb 2.4.0-beta~0bionic (debug)", "2.4.0", id="2.4-beta"),
        pytest.param("rethinkdb 2.4.0~0bionic (debug)", "2.4.0", id="2.4-debug"),
        pytest.param("rethinkdb 2.3.3~0jessie (GCC 4.9.2)", "2.3.3", id="2.3"),
        pytest.param("rethinkdb 2.3.6 (GCC 4.9.2)", "2.3.6", id="2.3-no-build"),
        pytest.param("rethinkdb 2.3.3", "2.3.3", id="no-compilation-string"),
    ],
)
def test_parse_version(version_string, expected_version):
    assert parse_version(version_string) == expected_version


@pytest.mark.parametrize("version_string", MALFORMED_VERSION_STRING_PARAMS)
def test_parse_malformed_version(version_string):
    with pytest.raises(ValueError):
        parse_version(version_string)


# --- types.py ---


def test_instance_typed_dict_is_not_total():
    assert Instance.__total__ is False
    assert Instance.__required_keys__ == frozenset()


# --- queries.py ---


def test_table_status_service_checks_map_true_to_ok_and_false_to_warning():
    service_check_columns = [col for col in DatabaseTableMetrics["columns"] if col.get("type") == "service_check"]
    assert len(service_check_columns) == 4
    for column in service_check_columns:
        assert column["status_map"] == {True: "OK", False: "WARNING"}


# --- check.py ---


def test_password_is_registered_as_secret():
    check = RethinkDBCheck("rethinkdb", {}, [{"password": "s3kr3t"}])
    assert check.sanitize("s3kr3t") == "********"


def test_version_metadata_query_is_registered():
    check = RethinkDBCheck("rethinkdb", {}, [{}])
    query_names = [query.query_data["name"] for query in check._query_manager.queries]
    assert "version_metadata" in query_names


def test_execute_raw_query_uses_cached_func_without_reimporting():
    check = RethinkDBCheck("rethinkdb", {}, [{}])
    rows = [("cached",)]
    check._query_funcs["bogus:path"] = lambda conn: rows
    assert check._execute_raw_query("bogus:path") is rows


def test_connect_submitting_service_checks_is_a_context_manager():
    check = RethinkDBCheck("rethinkdb", {}, [{}])
    cm = check.connect_submitting_service_checks()
    assert hasattr(cm, "__enter__")
    assert hasattr(cm, "__exit__")


def test_connect_passes_ca_certs_ssl_option_when_tls_ca_cert_set():
    check = RethinkDBCheck("rethinkdb", {}, [{"tls_ca_cert": "/path/to/ca.pem"}])
    with mock.patch("rethinkdb.r.connect") as mock_connect:
        with check.connect_submitting_service_checks():
            pass
    assert mock_connect.call_args.kwargs["ssl"] == {"ca_certs": "/path/to/ca.pem"}


def test_connect_reql_driver_error_is_caught_and_reraised(aggregator):
    check = RethinkDBCheck("rethinkdb", {}, [{}])
    with mock.patch("rethinkdb.r.connect", side_effect=rethinkdb.errors.ReqlDriverError("boom")):
        with pytest.raises(rethinkdb.errors.ReqlDriverError):
            with check.connect_submitting_service_checks():
                pass
    aggregator.assert_service_check("rethinkdb.can_connect", RethinkDBCheck.CRITICAL)


def test_connect_unexpected_error_is_caught_and_reraised(aggregator):
    check = RethinkDBCheck("rethinkdb", {}, [{}])
    with mock.patch("rethinkdb.r.connect", side_effect=ValueError("boom")):
        with pytest.raises(ValueError):
            with check.connect_submitting_service_checks():
                pass
    aggregator.assert_service_check("rethinkdb.can_connect", RethinkDBCheck.CRITICAL)


# --- queries_impl.py ---


def test_get_server_metrics_joins_stats_and_status_by_matching_server_name():
    matching_name = "".join(["server", "0"])
    now = dt.datetime.now(UTC)
    server_statuses = [
        {
            "name": "zzzz",
            "network": {"time_connected": now, "connected_to": {"a": True}},
            "process": {"time_started": now},
        },
        {"name": "aardvark", "network": {"time_connected": now, "connected_to": {}}, "process": {"time_started": now}},
        {
            "name": "server0",
            "network": {"time_connected": now, "connected_to": {"a": True, "b": True}},
            "process": {"time_started": now},
        },
    ]
    joined_server_stats = [
        {
            "left": {
                "query_engine": {
                    "client_connections": 1,
                    "clients_active": 2,
                    "queries_per_sec": 3,
                    "queries_total": 4,
                    "read_docs_per_sec": 5,
                    "read_docs_total": 6,
                    "written_docs_per_sec": 7,
                    "written_docs_total": 8,
                }
            },
            "right": {"name": matching_name, "tags": ["t"]},
        }
    ]
    with mock.patch("rethinkdb.ast.RqlQuery.run", side_effect=[server_statuses, joined_server_stats]):
        rows = queries_impl.get_server_metrics(conn=None)
    assert len(rows) == 1
    assert rows[0][0] == matching_name
    assert rows[0][11] == 2  # len(connected_to) from the correctly-matched 'server0' status entry.


def test_get_database_table_metrics_joins_stats_and_status_by_matching_table_name():
    matching_name = "".join(["heroes", ""])
    table_statuses = [
        {
            "name": "zzzz",
            "shards": [1],
            "status": {
                "ready_for_outdated_reads": False,
                "ready_for_reads": False,
                "ready_for_writes": False,
                "all_replicas_ready": False,
            },
        },
        {
            "name": "aardvark",
            "shards": [1, 2],
            "status": {
                "ready_for_outdated_reads": False,
                "ready_for_reads": False,
                "ready_for_writes": False,
                "all_replicas_ready": False,
            },
        },
        {
            "name": "heroes",
            "shards": [1, 2, 3],
            "status": {
                "ready_for_outdated_reads": True,
                "ready_for_reads": True,
                "ready_for_writes": True,
                "all_replicas_ready": True,
            },
        },
    ]
    joined_table_stats = [
        {
            "left": {"query_engine": {"read_docs_per_sec": 1, "written_docs_per_sec": 2}},
            "right": {"db": "doghouse", "name": matching_name},
        }
    ]
    with mock.patch("rethinkdb.ast.RqlQuery.run", side_effect=[joined_table_stats, table_statuses]):
        rows = queries_impl.get_database_table_metrics(conn=None)
    assert len(rows) == 1
    assert rows[0][4] == 3  # len(shards) from the correctly-matched 'heroes' status entry.
    assert rows[0][5] is True


def test_get_replica_metrics_returns_a_row_per_document():
    results = [
        {
            "table": {"name": "heroes", "db": "doghouse"},
            "server": {"name": "server1", "tags": ["server_tag:default"]},
            "replica": {"state": "ready"},
            "stats": {
                "query_engine": {
                    "read_docs_per_sec": 1,
                    "read_docs_total": 2,
                    "written_docs_per_sec": 3,
                    "written_docs_total": 4,
                },
                "storage_engine": {
                    "cache": {"in_use_bytes": 5},
                    "disk": {
                        "read_bytes_per_sec": 6,
                        "read_bytes_total": 7,
                        "written_bytes_per_sec": 8,
                        "written_bytes_total": 9,
                        "space_usage": {
                            "metadata_bytes": 10,
                            "data_bytes": 11,
                            "garbage_bytes": 12,
                            "preallocated_bytes": 13,
                        },
                    },
                },
            },
        }
    ]
    with mock.patch("rethinkdb.ast.RqlQuery.run", return_value=results):
        rows = queries_impl.get_replica_metrics(conn=None)
    assert rows == [
        ("heroes", "doghouse", "server1", ["server_tag:default"], "ready", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)
    ]


def test_get_table_status_metrics_returns_a_row_per_document():
    table_statuses = [
        {
            "name": "heroes",
            "db": "doghouse",
            "shards": [1, 2],
            "status": {
                "ready_for_outdated_reads": True,
                "ready_for_reads": True,
                "ready_for_writes": True,
                "all_replicas_ready": True,
            },
        }
    ]
    with mock.patch("rethinkdb.ast.RqlQuery.run", return_value=table_statuses):
        rows = queries_impl.get_table_status_metrics(conn=None)
    assert rows == [("heroes", "doghouse", 2, True, True, True, True)]


def test_get_shard_metrics_returns_a_row_per_shard():
    results = [
        {
            "table": {"name": "heroes", "db": "doghouse"},
            "replicas": ["server1", "server2"],
            "primary_replicas": ["server1"],
        },
        {"table": {"name": "heroes", "db": "doghouse"}, "replicas": ["server1"], "primary_replicas": ["server1"]},
    ]
    with mock.patch("rethinkdb.ast.RqlQuery.run", return_value=results):
        rows = queries_impl.get_shard_metrics(conn=None)
    assert rows == [
        (0, "heroes", "doghouse", 2, 1),
        (1, "heroes", "doghouse", 1, 1),
    ]


def test_get_job_metrics_returns_a_row_per_job_type():
    with mock.patch("rethinkdb.ast.RqlQuery.run", return_value={"query": 3}):
        rows = queries_impl.get_job_metrics(conn=None)
    assert rows == [("query", 3)]


def test_get_current_issues_metrics_merges_by_job_type_defaulting_to_zero():
    with mock.patch("rethinkdb.ast.RqlQuery.run", side_effect=[{"table_availability": 5}, {"table_readiness": 3}]):
        rows = queries_impl.get_current_issues_metrics(conn=None)
    assert rows == [("table_availability", 5, 0), ("table_readiness", 0, 3)]


def test_get_version_metadata_returns_empty_for_proxy_with_no_server_status():
    conn = mock.Mock()
    conn.server.return_value = {"id": "server1", "proxy": True}
    with mock.patch("rethinkdb.ast.RqlQuery.run", return_value=None):
        assert queries_impl.get_version_metadata(conn) == []
