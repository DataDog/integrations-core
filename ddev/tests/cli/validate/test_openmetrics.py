import pytest
# calico = v2
# cilium has v1 and v2
# maybe create a fake check without DEFAULT_METRIC_LIMIT?

'''
class ArangodbCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'arangodb'
    def __init__(self, name, init_config, instances):
        super(ArangodbCheck, self).__init__(name, init_config, instances)
'''

# Test cases
# If core or extras, should do validation
# if openmetrics v1 or v2, then should have DEFAULT_METRIC_LIMIT = 0
# if there are no DEFAULT_METRIC_LIMIT, then should output error
    # Error for single integration
    # error for multiple integrations
# if "ddev validate openmetrics", should include all integrations
# if "ddev validate openmetrics all", should include all integrations
# if "ddev validate openmetrics cilium", should include only arangodb

@pytest.mark.parametrize(
    "check_name", 
    [
        pytest.param(
            "aerospike",
            id="Aerospike check.py OpenMetricsV2"
        ),
        pytest.param(
            "amazon_msk",
            id="Amazon MSK amazon_msk.py OpenMetricsV1"
        ),
    ]
)
def test_openmetrics_pass_single_parameter(ddev, check_name, helpers, network_replay):
    # Not completely sure what this is doing
    network_replay('fixtures/openmetrics/metric_limit/success.yaml', record_mode='none')
    result = ddev("validate", "openmetrics", check_name)

    assert result.exit_code == 0, result.output

    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Validating DEFAULT_METRIC_LIMIT = 0 for OpenMetrics integrations ...
        OpenMetrics Metric limit

        Passed: 1
        """
    )

@pytest.mark.parametrize(
    "check_name, display_name, check_file", 
    [
        pytest.param(
            "arangodb",
            "ArangoDB",
            "check.py",
            id="Aerospike check.py OpenMetricsV2"
        ),
        pytest.param(
            "amazon_msk",
            "Amazon MSK",
            "amazon_msk.py",
            id="Amazon MSK amazon_msk.py OpenMetricsV1"
        ),
    ]
)
def test_openmetrics_fail_single_parameter(ddev, check_name, display_name, check_file, helpers, network_replay):
    network_replay('fixtures/openmetrics/metric_limit/fail.yaml', record_mode='none')
    result = ddev("validate", "openmetrics", check_name)

    assert result.exit_code == 1, result.output

    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Validating DEFAULT_METRIC_LIMIT = 0 for OpenMetrics integrations ...
        OpenMetrics Metric limit
        └── {display_name}
            └── check.py
                
                `DEFAULT_METRIC_LIMIT = 0` is missing

        Errors: 1
        """
    )
