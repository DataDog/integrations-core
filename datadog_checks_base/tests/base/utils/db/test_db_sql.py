# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

import pytest

from datadog_checks.base.utils.db.sql import compute_sql_signature, normalize_query_tag


class TestSQL:
    def test_compute_sql_signature(self):
        """
        This is a simple test which only exists to validate the consistency of query hashes
        when changes are made to the hashing algorithm. Changes to the hash can have
        product impact since the backend expects consistency with the APM resource hash.
        """
        assert '6db2e4f3905c3b5b' == compute_sql_signature('select * from dÒgs')
        assert '11b755a835280e8e' == compute_sql_signature('select * from dogs')
        assert 'd2a193f97126ad67' == compute_sql_signature('update dogs set name = ? where id = ?')

    @pytest.mark.parametrize(
        'arg,expected',
        [
            ('', ''),
            ('select * from dogs', 'select * from dogs'),
            # If you are debugging below cases and are confused, note the commas in the output are non-ascii commas
            ('select col1, col2, col3 from dogs', 'select col1， col2， col3 from dogs'),
            (
                'SELECT permission.id,permission.uuid, permission.name,permission.display_name, '
                'permission.description,permission.created_at, permission.modified_at, permission.group_name, '
                'permission.display_type, permission.restricted, permission.hidden, permission.meta FROM permission '
                'ORDER BY permission.id',
                'SELECT permission.id，permission.uuid， permission.name，permission.display_name， '
                'permission.description，permission.created_at， permission.modified_at， permission.group_name， '
                'permission.display_type， permission.restricted， permission.hidden， permission.meta FROM permission '
                'ORDER BY permission.id',
            ),
        ],
    )
    def test_normalize_query_tag(self, arg, expected):
        assert expected == normalize_query_tag(arg)
