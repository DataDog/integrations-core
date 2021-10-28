import logging

import mock
import pytest
import yaml

from datadog_checks.base import ConfigurationError
from datadog_checks.snmp.parsing import parse_metrics

from . import common

pytestmark = common.snmp_integration_only

logger = logging.getLogger(__name__)


@pytest.mark.unit
@pytest.mark.parametrize(
    'index_transform, expected_rules',
    [
        (pytest.param("[{'start': 1, 'end': 7}]", [slice(1, 8)], id="one_rule")),
        (
            pytest.param(
                "[{'start': 1, 'end': 7}, {'start': 10, 'end': 19}, ]", [slice(1, 8), slice(10, 20)], id="multi_rules"
            )
        ),
        (pytest.param("[{'start': 1, 'end': 1}]", [slice(1, 2)], id="one_value_index")),
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
      index_transform: {}
      tag: pdu_name
""".format(
        index_transform
    )

    results = parse_metrics(yaml.load(metrics), resolver=mock.MagicMock(), logger=logger, bulk_threshold=10)
    actual_transform_rules = results['parsed_metrics'][0].column_tags[0].index_slices
    assert actual_transform_rules == expected_rules


@pytest.mark.unit
@pytest.mark.parametrize(
    'index_transform, error_msg',
    [
        (pytest.param("[{'start': 1}]", "Transform rule must contain start and end", id="missing_end")),
        (pytest.param("[{'end': 1}]", "Transform rule must contain start and end", id="missing_start")),
        (pytest.param("[{'abc': 1}]", "Transform rule must contain start and end", id="invalid_keys")),
        (
            pytest.param(
                "[{'start': 1, 'end': 'abc'}]", "Transform rule start and end must be integers", id="invalid_end"
            )
        ),
        (
            pytest.param(
                "[{'start': 'abc', 'end': 2}]", "Transform rule start and end must be integers", id="invalid_start"
            )
        ),
        (
            pytest.param(
                "[{'start': 2, 'end': 1}]", "Transform rule end should be greater than start", id="end_must_be_greater"
            )
        ),
        (pytest.param("[{'start': -1, 'end': 1}]", "Transform rule start must be greater than 0", id="negative_value")),
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
      index_transform: {}
      tag: pdu_name
""".format(
        index_transform
    )

    with pytest.raises(ConfigurationError) as e:
        parse_metrics(yaml.load(metrics), resolver=mock.MagicMock(), logger=logger, bulk_threshold=10)
    assert error_msg in str(e.value)
