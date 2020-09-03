import logging

import mock
import pytest
import yaml

from datadog_checks.base import ConfigurationError
from datadog_checks.snmp.parsing import parse_metrics

from . import common

pytestmark = common.python_autodiscovery_only

logger = logging.getLogger(__name__)


@pytest.mark.unit
@pytest.mark.parametrize(
    'index_transform, expected_rules',
    [
        (pytest.param("1:8", [(1, 8)], id="one_rule")),
        (pytest.param("1:8,10:20", [(1, 8), (10, 20)], id="multi_rules")),
    ],
)
def test_parse_index_transform_ok_cases(index_transform, expected_rules):
    metrics = """
- MIB: CPI-UNITY-MIB
  table:
    OID: 1.3.6.1.4.1.30932.1.10.1.3.110
    name: cpiPduBranchTable
  symbols:
    - OID: 1.3.6.1.4.1.30932.1.10.1.3.110.1.9
      name: cpiPduBranchEnergy
  metric_tags:
    - column:
        OID: 1.3.6.1.4.1.30932.1.10.1.2.10.1.3
        name: cpiPduName
      table: cpiPduTable
      index_transform: "{}"
      tag: pdu_name
""".format(
        index_transform
    )

    results = parse_metrics(yaml.load(metrics), resolver=mock.MagicMock(), logger=logger, bulk_threshold=10)
    actual_transform_rules = results['parsed_metrics'][0].column_tags[0].index_transform_rules
    assert actual_transform_rules == expected_rules


@pytest.mark.unit
@pytest.mark.parametrize(
    'index_transform, error_msg',
    [
        (pytest.param("1:", "Invalid transform rule", id="one_rule")),
        (pytest.param("1:8:20", "Invalid transform rule", id="too_many_values")),
        (pytest.param("1", "Invalid transform rule", id="not_enough_values")),
        (pytest.param("1:2,3:8:20", "Invalid transform rule", id="multi_too_many_values")),
        (pytest.param("1:2,", "Invalid transform rule", id="empty_element")),
        (pytest.param("a:2", "Invalid transform rule", id="not_integer")),
    ],
)
def test_parse_index_transform_config_error(index_transform, error_msg):
    metrics = """
- MIB: CPI-UNITY-MIB
  table:
    OID: 1.3.6.1.4.1.30932.1.10.1.3.110
    name: cpiPduBranchTable
  symbols:
    - OID: 1.3.6.1.4.1.30932.1.10.1.3.110.1.9
      name: cpiPduBranchEnergy
  metric_tags:
    - column:
        OID: 1.3.6.1.4.1.30932.1.10.1.2.10.1.3
        name: cpiPduName
      table: cpiPduTable
      index_transform: "{}"
      tag: pdu_name
""".format(
        index_transform
    )

    with pytest.raises(ConfigurationError) as e:
        parse_metrics(yaml.load(metrics), resolver=mock.MagicMock(), logger=logger, bulk_threshold=10)
    assert error_msg in str(e.value)
