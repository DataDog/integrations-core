# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.aws import rds_parse_tags_from_endpoint


class TestRDS:
    @pytest.mark.parametrize(
        'test_case,expected',
        [
            (None, []),
            ('', []),
            ('localhost', []),
            ('/var/run/postgres.sock', []),
            (
                ' my_db.cfxdfe8cpixl.us-east-2.rds.amazonaws.com ',
                [
                    'dbinstanceidentifier:my_db',
                    'hostname:my_db.cfxdfe8cpixl.us-east-2.rds.amazonaws.com',
                    'host:my_db.cfxdfe8cpixl.us-east-2.rds.amazonaws.com',
                    'region:us-east-2',
                ],
            ),
            (
                'customers-04.cfxdfe8cpixl.us-west-2.rds.amazonaws.com',
                [
                    'dbinstanceidentifier:customers-04',
                    'hostname:customers-04.cfxdfe8cpixl.us-west-2.rds.amazonaws.com',
                    'host:customers-04.cfxdfe8cpixl.us-west-2.rds.amazonaws.com',
                    'region:us-west-2',
                ],
            ),
            (
                'dd-metrics.cluster-ro-cfxdfe8cpixl.ap-east-1.rds.amazonaws.com',
                ['dbclusteridentifier:dd-metrics', 'region:ap-east-1'],
            ),
            (
                'dd-metrics.cluster-cfxdfe8cpixl.ap-east-1.rds.amazonaws.com',
                ['dbclusteridentifier:dd-metrics', 'region:ap-east-1'],
            ),
        ],
    )
    def test_parse_tags_from_endpoint(self, test_case, expected):
        assert rds_parse_tags_from_endpoint(test_case) == expected
