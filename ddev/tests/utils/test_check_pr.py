import json
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Callable

import pytest

from ddev.utils.scripts.check_pr import main


@dataclass
class ContextForTesting:
    pr_fpath: Path
    diff_fpath: Path
    command: Callable[[], None]


@pytest.fixture
def testing_context(monkeypatch, tmp_path):
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    pr_fpath = tmp_path / 'pr.json'
    pr_fpath.write_text(
        json.dumps({'pull_request': {'number': 123, 'html_url': 'http://github.com/repo/pull/123', 'labels': []}})
    )
    diff_fpath = tmp_path / 'diff'
    return ContextForTesting(
        pr_fpath=pr_fpath,
        diff_fpath=diff_fpath,
        command=partial(main, args=['changelog', '--diff-file', str(diff_fpath), '--pr-file', str(pr_fpath)]),
    )


EXAMPLE_NEEDS_CHANGELOG = '''\
diff --git a/snowflake/datadog_checks/snowflake/queries.py b/snowflake/datadog_checks/snowflake/queries.py
index 9e83ef8f4b0c..d7d3c5fb62ff 100644
--- a/snowflake/datadog_checks/snowflake/queries.py
+++ b/snowflake/datadog_checks/snowflake/queries.py
@@ -191,12 +191,15 @@
 PipeHistory = {
     'name': 'pipe.metrics',
     'query': (
-        'select pipe_name, avg(credits_used), sum(credits_used), avg(bytes_inserted), sum(bytes_inserted), '
-        'avg(files_inserted), sum(files_inserted) from pipe_usage_history '
-        'where start_time >= DATEADD(hour, -24, current_timestamp()) group by 1;'
+        'avg(files_inserted), sum(files_inserted) from pipe_usage_history as history '
+        'join snowflake.account_usage.pipes p on p.pipe_id = history.pipe_id '
+        'where start_time >= DATEADD(hour, -24, current_timestamp()) group by 1,2,3;'
     ),
     'columns': [
         {'name': 'pipe', 'type': 'tag'},
+        {'name': 'pipe_schema', 'type': 'tag'},
+        {'name': 'pipe_catalog', 'type': 'tag'},
         {'name': 'pipe.credits_used.avg', 'type': 'gauge'},
         {'name': 'pipe.credits_used.sum', 'type': 'gauge'},
         {'name': 'pipe.bytes_inserted.avg', 'type': 'gauge'},
'''

EXAMPLE_VALID_CHANGELOG = '''\
diff --git a/snowflake/changelog.d/123.added b/snowflake/changelog.d/123.added
new file mode 100644
index 000000000000..dfad2dae7569
--- /dev/null
+++ b/snowflake/changelog.d/123.added
@@ -0,0 +1 @@
+Added `pipe_schema` and `pipe_catalog` tags to snowpipe metrics.
\\ No newline at end of file
'''

EXAMPLE_CHANGELOG_WITH_INVALID_CHANGE_TYPE = '''\
diff --git a/snowflake/changelog.d/123.add b/snowflake/changelog.d/123.add
new file mode 100644
index 000000000000..dfad2dae7569
--- /dev/null
+++ b/snowflake/changelog.d/123.add
@@ -0,0 +1 @@
+Added `pipe_schema` and `pipe_catalog` tags to snowpipe metrics.
\\ No newline at end of file
'''

EXAMPLE_CHANGELOG_WITH_WRONG_PR_NUM = '''\
diff --git a/snowflake/changelog.d/321.added b/snowflake/changelog.d/321.added
new file mode 100644
index 000000000000..dfad2dae7569
--- /dev/null
+++ b/snowflake/changelog.d/321.added
@@ -0,0 +1 @@
+Added `pipe_schema` and `pipe_catalog` tags to snowpipe metrics.
\\ No newline at end of file
'''

EXAMPLE_NO_CHANGELOG_NEEDED = '''\
diff --git a/mysql/assets/monitors/replica_running.json b/mysql/assets/monitors/replica_running.json
index 9671b8a6fb1c..69340c11d868 100644
--- a/mysql/assets/monitors/replica_running.json
+++ b/mysql/assets/monitors/replica_running.json
@@ -2,11 +2,11 @@
   "version": 2,
   "created_at": "2021-02-16",
   "last_updated_at": "2023-07-24",
-  "title": "Replica {{host.name}} is not running properly",
+  "title": "MySQL database replica is not running properly",
   "tags": [
     "integration:mysql"
   ],
-  "description": "Notify your team when a replica is not running properly.",
+  "description": "A database replica is a copy of a database that is synchronized with the original database.",
   "definition": {
     "message": "Replica_IO_Running and/or Replica_SQL_Running is not running on replica {{host.name}}.",
     "name": "[MySQL] Replica {{host.name}} is not running properly",
'''


@pytest.mark.parametrize(
    'diff_content',
    [
        pytest.param(EXAMPLE_NEEDS_CHANGELOG + EXAMPLE_VALID_CHANGELOG, id='changelog entry needed and valid'),
        pytest.param(EXAMPLE_NO_CHANGELOG_NEEDED, id='no changelog needed'),
    ],
)
def test_validation_passes(diff_content, testing_context, capsys):
    testing_context.diff_fpath.write_text(diff_content)

    testing_context.command()
    captured = capsys.readouterr()
    assert captured.out == ""


@pytest.mark.parametrize(
    'diff_content, expected_out',
    [
        pytest.param(
            EXAMPLE_NEEDS_CHANGELOG,
            (
                'Package "snowflake" has changes that require a changelog. '
                'Please run `ddev release changelog new` to add it.\n'
                '::error file=snowflake/changelog.d/123.fixed,line=0::'
                'Package "snowflake" has changes that require a changelog. '
                'Please run `ddev release changelog new` to add it.\n'
            ),
            id='missing needed changelog',
        ),
        pytest.param(
            EXAMPLE_NEEDS_CHANGELOG + EXAMPLE_CHANGELOG_WITH_WRONG_PR_NUM,
            (
                'Your changelog entry has the wrong PR number. To fix this please run:\n'
                'mv snowflake/changelog.d/321.added snowflake/changelog.d/123.added\n'
                '::error file=snowflake/changelog.d/321.added,line=0::'
                'Your changelog entry has the wrong PR number. To fix this please run:%0A'
                'mv snowflake/changelog.d/321.added snowflake/changelog.d/123.added\n'
            ),
            id='changelog has wrong PR number',
        ),
        pytest.param(
            EXAMPLE_NEEDS_CHANGELOG + EXAMPLE_CHANGELOG_WITH_INVALID_CHANGE_TYPE,
            (
                'Your changelog entry "snowflake/changelog.d/123.add" has an invalid change type, '
                'please rename the file. Valid types are:\n'
                'added changed deprecated fixed removed security\n'
                '::error file=snowflake/changelog.d/123.add,line=0::'
                'Your changelog entry "snowflake/changelog.d/123.add" has an invalid change type, '
                'please rename the file. Valid types are:%0A'
                'added changed deprecated fixed removed security\n'
            ),
            id='changelog has invalid change type',
        ),
        pytest.param(
            EXAMPLE_NO_CHANGELOG_NEEDED + EXAMPLE_VALID_CHANGELOG,
            (
                "You added a changelog, but it's not needed for this change. To fix this please run:\n"
                'rm snowflake/changelog.d/123.added\n'
                "::error file=snowflake/changelog.d/123.added,line=0::You added a changelog, but it's not needed "
                "for this change. To fix this please run:%0Arm snowflake/changelog.d/123.added\n"
            ),
            id='changelog not needed',
        ),
    ],
)
def test_validation_fails(diff_content, expected_out, testing_context, capsys):
    testing_context.diff_fpath.write_text(diff_content)

    with pytest.raises(SystemExit) as e:
        testing_context.command()
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == expected_out
