# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.dev import get_here
from datadog_checks.postfix import PostfixCheck

pytestmark = pytest.mark.unit

MOCK_VERSION = "1.3.1"
MOCK_VERSION_OUTPUT = ("mail_version = {}".format(MOCK_VERSION), None, None)


def test_check_postqueue_mode_counts_active_hold_and_deferred_from_fixture(aggregator):
    instance = {"config_directory": "/etc/postfix", "tags": ["foo:bar"]}
    check = PostfixCheck("postfix", {"postqueue": True}, [instance])
    common_tags = ["instance:/etc/postfix", "foo:bar"]

    filepath = os.path.join(get_here(), "fixtures", "postqueue_p.txt")
    with open(filepath, "r") as f:
        mocked_output = f.read()

    with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
        s.side_effect = [(False, None, None), (mocked_output, None, None), MOCK_VERSION_OUTPUT]
        check.check(instance)

    aggregator.assert_metric("postfix.queue.size", 1, tags=common_tags + ["queue:active"])
    aggregator.assert_metric("postfix.queue.size", 1, tags=common_tags + ["queue:hold"])
    aggregator.assert_metric("postfix.queue.size", 2, tags=common_tags + ["queue:deferred"])


def test_check_postqueue_mode_reports_zero_counts_when_queue_is_empty(aggregator):
    instance = {"config_directory": "/etc/postfix"}
    check = PostfixCheck("postfix", {"postqueue": True}, [instance])
    common_tags = ["instance:/etc/postfix"]

    with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
        s.side_effect = [(False, None, None), ("Mail queue is empty", None, None), MOCK_VERSION_OUTPUT]
        check.check(instance)

    aggregator.assert_metric("postfix.queue.size", 0, tags=common_tags + ["queue:active"])
    aggregator.assert_metric("postfix.queue.size", 0, tags=common_tags + ["queue:hold"])
    aggregator.assert_metric("postfix.queue.size", 0, tags=common_tags + ["queue:deferred"])


def test_collect_metadata(aggregator, datadog_agent, tmp_path):
    # TODO: Migrate this test as e2e test when it's possible to retrieve the metadata from the Agent
    (tmp_path / "active").mkdir()
    instance = {"directory": str(tmp_path), "queues": ["active"]}
    check = PostfixCheck("postfix", {}, [instance])
    check.check_id = "test:123"

    with mock.patch("datadog_checks.postfix.postfix.os.geteuid", return_value=0):
        with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
            s.side_effect = [MOCK_VERSION_OUTPUT]
            check.check(instance)

    major, minor, patch = MOCK_VERSION.split(".")
    version_metadata = {
        "version.scheme": "semver",
        "version.major": major,
        "version.minor": minor,
        "version.patch": patch,
        "version.raw": MOCK_VERSION,
    }

    datadog_agent.assert_metadata("test:123", version_metadata)


def test_check_dispatches_to_postqueue_stats_when_enabled(aggregator):
    instance = {"config_directory": "/etc/postfix", "tags": ["foo:bar"]}
    check = PostfixCheck("postfix", {"postqueue": True}, [instance])

    with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
        s.side_effect = [
            ("authorized_mailq_users = dd-agent", None, None),
            ("Mail queue is empty", None, None),
            MOCK_VERSION_OUTPUT,
        ]
        check.check(instance)

    aggregator.assert_metric("postfix.queue.size", 0, tags=["foo:bar", "queue:active", "instance:/etc/postfix"])


def test_check_dispatches_to_queue_count_by_default(aggregator, tmp_path):
    (tmp_path / "active").mkdir()
    instance = {"directory": str(tmp_path), "queues": ["active"], "tags": ["foo:bar"]}
    check = PostfixCheck("postfix", {}, [instance])

    with mock.patch("datadog_checks.postfix.postfix.os.geteuid", return_value=0):
        with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
            s.side_effect = [MOCK_VERSION_OUTPUT]
            check.check(instance)

    aggregator.assert_metric(
        "postfix.queue.size", 0, tags=["foo:bar", "queue:active", "instance:{}".format(tmp_path.name)]
    )


def test_get_config_classic_mode_requires_queues_and_directory():
    check = PostfixCheck("postfix", {}, [{}])
    with pytest.raises(Exception, match="using sudo: missing required yaml config entry"):
        check.check({"directory": "/etc/postfix"})


def test_get_config_classic_mode_requires_directory_when_queues_set():
    check = PostfixCheck("postfix", {}, [{}])
    with pytest.raises(Exception, match="using sudo: missing required yaml config entry"):
        check.check({"queues": ["active"]})


def test_get_config_default_postqueue_is_classic_mode():
    check = PostfixCheck("postfix", {}, [{}])
    with pytest.raises(Exception, match="using sudo: missing required yaml config entry"):
        check.check({})


def test_get_config_logs_postqueue_default_value():
    check = PostfixCheck("postfix", {}, [{}])
    with mock.patch.object(check.log, "debug") as debug_mock:
        with pytest.raises(Exception):
            check.check({})

    debug_mock.assert_any_call("postqueue: %s", False)


def test_get_config_postqueue_mode_skips_queues_and_directory_check(aggregator):
    instance = {"config_directory": "/etc/postfix"}
    check = PostfixCheck("postfix", {"postqueue": True}, [instance])

    with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
        s.side_effect = [
            ("authorized_mailq_users = dd-agent", None, None),
            ("Mail queue is empty", None, None),
            MOCK_VERSION_OUTPUT,
        ]
        check.check(instance)

    aggregator.assert_metric("postfix.queue.size", 0, tags=["queue:active", "instance:/etc/postfix"])


def test_get_config_postqueue_mode_requires_config_directory():
    check = PostfixCheck("postfix", {"postqueue": True}, [{}])
    with pytest.raises(Exception, match='using postqueue: missing required yaml "config_directory" entry'):
        check.check({})


def test_get_postqueue_stats_authorized_users_call_args():
    instance = {"config_directory": "/etc/postfix"}
    check = PostfixCheck("postfix", {"postqueue": True}, [instance])
    with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
        s.side_effect = [
            ("authorized_mailq_users = dd-agent", None, None),
            ("Mail queue is empty", None, None),
            MOCK_VERSION_OUTPUT,
        ]
        check.check(instance)

    assert s.call_args_list[0] == mock.call(["postconf", "authorized_mailq_users"], check.log, False)


def test_get_postqueue_stats_logs_authorized_users_value():
    instance = {"config_directory": "/etc/postfix"}
    check = PostfixCheck("postfix", {"postqueue": True}, [instance])
    with mock.patch.object(check.log, "debug") as debug_mock:
        with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
            s.side_effect = [
                ("authorized_mailq_users = dd-agent", None, None),
                ("Mail queue is empty", None, None),
                MOCK_VERSION_OUTPUT,
            ]
            check.check(instance)

    debug_mock.assert_any_call("authorized_mailq_users : %s", "dd-agent")


def test_get_postqueue_stats_postqueue_call_args():
    instance = {"config_directory": "/etc/postfix"}
    check = PostfixCheck("postfix", {"postqueue": True}, [instance])
    with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
        s.side_effect = [(False, None, None), ("Mail queue is empty", None, None), MOCK_VERSION_OUTPUT]
        check.check(instance)

    assert s.call_args_list[1] == mock.call(["postqueue", "-c", "/etc/postfix", "-p"], check.log, False)


def test_get_postqueue_stats_single_entry_line_is_ignored(aggregator):
    instance = {"config_directory": "/etc/postfix"}
    check = PostfixCheck("postfix", {"postqueue": True}, [instance])
    with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
        s.side_effect = [
            (False, None, None),
            ("3xWyLP6Nmfz23fk deferred-entry", None, None),
            MOCK_VERSION_OUTPUT,
        ]
        check.check(instance)

    aggregator.assert_metric("postfix.queue.size", 0, tags=["instance:/etc/postfix", "queue:deferred"])


def test_get_postqueue_stats_two_entry_lines_are_processed(aggregator):
    instance = {"config_directory": "/etc/postfix"}
    check = PostfixCheck("postfix", {"postqueue": True}, [instance])
    with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
        s.side_effect = [(False, None, None), ("entry-one *\nentry-two *", None, None), MOCK_VERSION_OUTPUT]
        check.check(instance)

    aggregator.assert_metric("postfix.queue.size", 2, tags=["instance:/etc/postfix", "queue:active"])


def test_get_postqueue_stats_ignores_lines_when_queue_reported_empty(aggregator):
    instance = {"config_directory": "/etc/postfix"}
    check = PostfixCheck("postfix", {"postqueue": True}, [instance])
    with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
        s.side_effect = [
            (False, None, None),
            ("Mail queue is empty\nextra alnum line", None, None),
            MOCK_VERSION_OUTPUT,
        ]
        check.check(instance)

    aggregator.assert_metric("postfix.queue.size", 0, tags=["instance:/etc/postfix", "queue:deferred"])


def test_get_postqueue_stats_deferred_check_uses_single_char_prefix(aggregator):
    instance = {"config_directory": "/etc/postfix"}
    check = PostfixCheck("postfix", {"postqueue": True}, [instance])
    with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
        s.side_effect = [
            (False, None, None),
            ("entry-one *\n3 deferred-entry", None, None),
            MOCK_VERSION_OUTPUT,
        ]
        check.check(instance)

    aggregator.assert_metric("postfix.queue.size", 1, tags=["instance:/etc/postfix", "queue:deferred"])


def test_get_queue_count_raises_when_queue_directory_missing(tmp_path):
    check = PostfixCheck("postfix", {}, [{}])
    instance = {"directory": str(tmp_path), "queues": ["missing-queue"]}
    with pytest.raises(Exception, match="does not exist"):
        check.check(instance)


def test_get_queue_count_root_sums_files_in_queue(aggregator, tmp_path):
    queue_dir = tmp_path / "active"
    queue_dir.mkdir()
    (queue_dir / "msg1").write_text("a")
    (queue_dir / "msg2").write_text("b")

    instance = {"directory": str(tmp_path), "queues": ["active"], "tags": ["foo:bar"]}
    check = PostfixCheck("postfix", {}, [instance])
    with mock.patch("datadog_checks.postfix.postfix.os.geteuid", return_value=0):
        with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
            s.side_effect = [MOCK_VERSION_OUTPUT]
            check.check(instance)

    aggregator.assert_metric(
        "postfix.queue.size", 2, tags=["foo:bar", "queue:active", "instance:{}".format(tmp_path.name)]
    )


def test_get_queue_count_positive_non_root_euid_uses_sudo_find(aggregator, tmp_path):
    queue_dir = tmp_path / "active"
    queue_dir.mkdir()

    instance = {"directory": str(tmp_path), "queues": ["active"]}
    check = PostfixCheck("postfix", {}, [instance])
    with mock.patch("datadog_checks.postfix.postfix.os.geteuid", return_value=1000):
        with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
            s.side_effect = [(None, None, 0), ("file1\nfile2\nfile3", None, None), MOCK_VERSION_OUTPUT]
            check.check(instance)

    aggregator.assert_metric("postfix.queue.size", 3, tags=["queue:active", "instance:{}".format(tmp_path.name)])
    assert s.call_args_list[0] == mock.call(["sudo", "-l"], check.log, False)
    assert s.call_args_list[1] == mock.call(
        ["sudo", "-u", "root", "find", str(queue_dir), "-type", "f"], check.log, False
    )


def test_get_queue_count_negative_euid_uses_sudo_find(aggregator, tmp_path):
    queue_dir = tmp_path / "active"
    queue_dir.mkdir()

    instance = {"directory": str(tmp_path), "queues": ["active"]}
    check = PostfixCheck("postfix", {}, [instance])
    with mock.patch("datadog_checks.postfix.postfix.os.geteuid", return_value=-1):
        with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
            s.side_effect = [(None, None, 0), ("file1", None, None), MOCK_VERSION_OUTPUT]
            check.check(instance)

    aggregator.assert_metric("postfix.queue.size", 1, tags=["queue:active", "instance:{}".format(tmp_path.name)])


def test_get_queue_count_raises_when_sudo_check_fails(tmp_path):
    (tmp_path / "active").mkdir()
    instance = {"directory": str(tmp_path), "queues": ["active"]}

    check = PostfixCheck("postfix", {}, [instance])
    with mock.patch("datadog_checks.postfix.postfix.os.geteuid", return_value=1000):
        with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
            s.side_effect = [(None, None, 1)]
            with pytest.raises(Exception, match="does not have sudo access"):
                check.check(instance)


def test_get_queue_count_raises_when_sudo_check_returns_negative_exit_code(tmp_path):
    (tmp_path / "active").mkdir()
    instance = {"directory": str(tmp_path), "queues": ["active"]}

    check = PostfixCheck("postfix", {}, [instance])
    with mock.patch("datadog_checks.postfix.postfix.os.geteuid", return_value=1000):
        with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
            s.side_effect = [(None, None, -1)]
            with pytest.raises(Exception, match="does not have sudo access"):
                check.check(instance)


def test_collect_metadata_call_args(tmp_path):
    (tmp_path / "active").mkdir()
    instance = {"directory": str(tmp_path), "queues": ["active"]}
    check = PostfixCheck("postfix", {}, [instance])

    with mock.patch("datadog_checks.postfix.postfix.os.geteuid", return_value=0):
        with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output") as s:
            s.side_effect = [MOCK_VERSION_OUTPUT]
            check.check(instance)

    assert s.call_args_list[0] == mock.call(["postconf", "mail_version"], check.log, False)


def test_collect_metadata_swallows_subprocess_errors(aggregator, tmp_path):
    (tmp_path / "active").mkdir()
    instance = {"directory": str(tmp_path), "queues": ["active"]}
    check = PostfixCheck("postfix", {}, [instance])

    with mock.patch("datadog_checks.postfix.postfix.os.geteuid", return_value=0):
        with mock.patch("datadog_checks.postfix.postfix.get_subprocess_output", side_effect=Exception("boom")):
            check.check(instance)

    aggregator.assert_metric("postfix.queue.size", 0, tags=["queue:active", "instance:{}".format(tmp_path.name)])
