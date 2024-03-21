# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.db.sql_commenter import add_sql_comment, generate_sql_comment


class TestSQLCommenter:
    def test_generate_sql_comment(self):
        assert generate_sql_comment(foo='bar', baz='qux') == "/* foo='bar',baz='qux' */"

    def test_generate_sql_comment_empty(self):
        assert generate_sql_comment() == ""

    def test_generate_sql_comment_none(self):
        assert generate_sql_comment(foo=None, baz='qux') == "/* baz='qux' */"

    @pytest.mark.parametrize(
        'sql,prepand,expected',
        [
            pytest.param('SELECT * FROM table', True, "/* foo='bar',baz='qux' */ SELECT * FROM table", id='prepand'),
            pytest.param('SELECT * FROM table', False, "SELECT * FROM table /* foo='bar',baz='qux' */", id='append'),
            pytest.param(
                'SELECT * FROM table;', False, "SELECT * FROM table /* foo='bar',baz='qux' */;", id='append_semicolon'
            ),
            pytest.param('', True, '', id='empty_sql'),
        ],
    )
    def test_add_sql_comment(self, sql, prepand, expected):
        assert add_sql_comment(sql, prepand, foo='bar', baz='qux') == expected

    def test_add_sql_comment_empty(self):
        assert add_sql_comment('SELECT * FROM table') == 'SELECT * FROM table'
