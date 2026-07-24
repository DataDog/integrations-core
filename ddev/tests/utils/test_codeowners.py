# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.utils.codeowners import CodeOwners, parse_owner

SAMPLE = """
# A comment line is ignored.
*                              @DataDog/agent-integrations
/postgres/                     @DataDog/database-monitoring
/foo/assets/logs/              @DataDog/logs-integrations-reviewers
/with\\ space/                 @DataDog/agent-integrations
[Section]
/sectioned/                    @DataDog/agent-integrations
"""


def test_team_match():
    co = CodeOwners(SAMPLE)
    assert co.of('/postgres/datadog_checks/postgres/check.py') == [('TEAM', '@DataDog/database-monitoring')]


def test_logs_team_match():
    co = CodeOwners(SAMPLE)
    assert ('TEAM', '@DataDog/logs-integrations-reviewers') in co.of('/foo/assets/logs/')


def test_default_owner_fallback():
    co = CodeOwners(SAMPLE)
    assert co.of('/unmatched/path.py') == [('TEAM', '@DataDog/agent-integrations')]


def test_path_with_escaped_space():
    co = CodeOwners(SAMPLE)
    assert co.of('/with space/file.txt') == [('TEAM', '@DataDog/agent-integrations')]


def test_section_name_tracking():
    co = CodeOwners(SAMPLE)
    assert co.section_name('/sectioned/file.py') == 'Section'
    assert co.section_name('/postgres/check.py') is None


def test_empty_owner_returns_empty_list():
    co = CodeOwners('/orphan/\n')
    assert co.of('/orphan/x') == []


def test_parse_owner_kinds():
    assert parse_owner('@DataDog/agent-integrations') == ('TEAM', '@DataDog/agent-integrations')
    assert parse_owner('@octocat') == ('USERNAME', '@octocat')
    assert parse_owner('dev@example.com') == ('EMAIL', 'dev@example.com')
    assert parse_owner('not-an-owner') is None


def test_comments_and_blank_lines_ignored():
    co = CodeOwners('# all comments\n\n  \n')
    assert co.paths == []


def test_matching_lines_yields_in_reverse_priority():
    co = CodeOwners(
        """
*           @DataDog/agent-integrations
/foo/       @DataDog/team-a
"""
    )
    # The most specific rule wins for `of` (last wins => listed first after reverse).
    assert co.of('/foo/bar') == [('TEAM', '@DataDog/team-a')]
