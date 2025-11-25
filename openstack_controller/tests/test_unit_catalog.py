# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.openstack_controller.api.catalog import Catalog


class TestCatalog:
    @pytest.mark.parametrize(
        ('service_type', 'endpoint_url', 'expected_url'),
        [
            pytest.param('identity', 'http://127.0.0.1:5000/v3', 'http://127.0.0.1:5000', id='identity v3'),
            pytest.param(
                'identity', 'http://127.0.0.1:5000/v3/', 'http://127.0.0.1:5000', id='identity v3 trailing slash'
            ),
            pytest.param('identity', 'http://127.0.0.1:5000/v2.0', 'http://127.0.0.1:5000', id='identity v2.0'),
            pytest.param('identity', 'http://127.0.0.1:5000/v1', 'http://127.0.0.1:5000', id='identity v1'),
            pytest.param('identity', 'http://127.0.0.1:5000', 'http://127.0.0.1:5000', id='identity no version'),
            pytest.param(
                'compute',
                'http://127.0.0.1:8774/v2.1/project123',
                'http://127.0.0.1:8774/v2.1/project123',
                id='compute keeps version',
            ),
            pytest.param(
                'network', 'http://127.0.0.1:9696/v2.0', 'http://127.0.0.1:9696/v2.0', id='network keeps version'
            ),
            pytest.param(
                'block-storage',
                'http://127.0.0.1:8776/v3/project123',
                'http://127.0.0.1:8776/v3/project123',
                id='block-storage keeps version',
            ),
        ],
    )
    def test_get_endpoint_by_type_version_handling(self, service_type, endpoint_url, expected_url):
        """Test that identity endpoints strip version suffix while other services preserve it"""
        catalog_data = [
            {
                'type': service_type,
                'endpoints': [
                    {
                        'interface': 'public',
                        'region_id': None,
                        'url': endpoint_url,
                    }
                ],
            }
        ]
        catalog = Catalog(catalog_data, None, None)
        endpoint = catalog.get_endpoint_by_type([service_type])
        assert endpoint == expected_url
