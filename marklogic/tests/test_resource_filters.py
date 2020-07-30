# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, List

import mock
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.marklogic import MarklogicCheck
from datadog_checks.marklogic.config import Config

from .common import INSTANCE_FILTERS, read_fixture_file


def test_build_resource_filters():
    # type: () -> None
    conf = Config(INSTANCE_FILTERS)

    assert len(conf.resource_filters['included']) == 2
    assert conf.resource_filters['included'][0].resource_type == 'forests'
    assert conf.resource_filters['included'][0].regex.pattern == "^S[a-z]*"
    assert conf.resource_filters['included'][0].is_included is True
    assert conf.resource_filters['included'][0].group is None
    assert conf.resource_filters['included'][1].resource_type == 'servers'
    assert conf.resource_filters['included'][1].regex.pattern == "Admin"
    assert conf.resource_filters['included'][1].is_included is True
    assert conf.resource_filters['included'][1].group == 'Default'

    assert len(conf.resource_filters['excluded']) == 1
    assert conf.resource_filters['excluded'][0].resource_type == 'forests'
    assert conf.resource_filters['excluded'][0].regex.pattern == "^Sch*"
    assert conf.resource_filters['excluded'][0].is_included is False
    assert conf.resource_filters['excluded'][0].group is None

    # Configuration error: no pattern
    with pytest.raises(ConfigurationError) as e:
        Config.build_resource_filters([{}])
        assert 'A resource filter requires at least a pattern and a resource_type' in str(e)
    # Configuration error: no resource_type
    with pytest.raises(ConfigurationError) as e:
        Config.build_resource_filters([{'pattern': 'abc'}])
        assert 'A resource filter requires at least a pattern and a resource_type' in str(e)
    # Configuration error: wrong resource_type
    with pytest.raises(ConfigurationError) as e:
        Config.build_resource_filters([{'pattern': 'abc', 'resource_type': 'datadog'}])
        assert 'Unknown resource_type: datadog' in str(e)


def test_get_resources_to_monitor():
    # type: () -> None
    check = MarklogicCheck('marklogic', {}, [INSTANCE_FILTERS])
    return_value = read_fixture_file('query/cluster-query.yaml')

    # Expected output when there is no exclude list
    complete_filtered = {
        'forests': [
            {'name': 'Security', 'id': '1112331563215633422', 'type': 'forests', 'uri': '/forests/Security'},
            {'name': 'Schemas', 'id': '5750304059804042419', 'type': 'forests', 'uri': '/forests/Schemas'},
        ],
        'databases': [],
        'hosts': [],
        'servers': [
            {
                'name': 'Admin',
                'id': '9403936238896063877',
                'type': 'servers',
                'uri': "/servers/Admin?group-id=Default",
                'group': 'Default',
            }
        ],
    }  # type: Dict[str, List[Any]]

    with mock.patch('datadog_checks.marklogic.api.MarkLogicApi._get_raw_resources', return_value=return_value):
        # Called in the check function
        check.resources = check.api.get_resources()
        # Include list + exclude list
        filtered_res = check.get_resources_to_monitor()
        assert filtered_res == {
            'forests': [complete_filtered['forests'][0]],
            'databases': [],
            'hosts': [],
            'servers': complete_filtered['servers'],
        }

        # No exclude list
        check.config.resource_filters['excluded'] = []
        filtered_res = check.get_resources_to_monitor()
        assert filtered_res == complete_filtered

        # Useless exclude list
        check.config.resource_filters['excluded'] = check.config.build_resource_filters(
            [{'resource_type': 'forest', 'pattern': 'Security', 'group': 'Default'}]
        )['excluded']
        filtered_res = check.get_resources_to_monitor()
        assert filtered_res == complete_filtered

        # No include list
        check.config.resource_filters['included'] = []
        filtered_res = check.get_resources_to_monitor()
        assert filtered_res == {
            'forests': [],
            'databases': [],
            'hosts': [],
            'servers': [],
        }
