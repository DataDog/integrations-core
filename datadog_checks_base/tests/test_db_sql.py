# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.db.sql import compute_sql_signature


class TestSQL:
    def test_compute_sql_signature(self):
        """
        This is a simple test which only exists to validate the consistency of query hashes
        when changes are made to the hashing algorithm. Changes to the hash can have
        product impact since the backend expects consistency with the APM resource hash.
        """
        assert '11b755a835280e8e' == compute_sql_signature('select * from dogs')
        assert 'd2a193f97126ad67' == compute_sql_signature('update dogs set name = ? where id = ?')
