import pytest


@pytest.mark.parametrize(
    "check_name, check_count",
    [
        pytest.param("aerospike", 1, id="Aerospike check.py OpenMetricsV2"),
        pytest.param("amazon_msk", 2, id="Amazon MSK amazon_msk.py OpenMetricsV1 and V2"),
    ],
)
def test_openmetrics_pass_single_parameter(ddev, check_name, check_count, helpers, network_replay):
    # Not completely sure what this is doing
    network_replay('fixtures/openmetrics/metric_limit/success.yaml', record_mode='none')
    result = ddev("validate", "openmetrics", check_name)

    assert result.exit_code == 0, result.output

    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Validating DEFAULT_METRIC_LIMIT = 0 for OpenMetrics integrations ...
        OpenMetrics Metric limit

        Passed: {check_count}
        """
    )


def test_openmetrics_fail_single_parameter(ddev, helpers, repository, network_replay):
    missing_metric_limit = '''
            class ArangodbCheck(OpenMetricsBaseCheckV2, ConfigMixin):
            __NAMESPACE__ = 'arangodb'
            def __init__(self, name, init_config, instances):
                super(ArangodbCheck, self).__init__(name, init_config, instances)
        '''
    network_replay('fixtures/openmetrics/metric_limit/fail.yaml', record_mode='none')

    check = "arangodb"
    check_file = repository.path / check / "datadog_checks" / check / "check.py"

    with open(check_file, "w") as f:
        f.write(missing_metric_limit)

    result = ddev("validate", "openmetrics", "arangodb")

    assert result.exit_code == 1, result.output

    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Validating DEFAULT_METRIC_LIMIT = 0 for OpenMetrics integrations ...
        OpenMetrics Metric limit
        └── ArangoDB
            └── check.py

                `DEFAULT_METRIC_LIMIT = 0` is missing

        Errors: 1
        """
    )


@pytest.mark.parametrize(
    "repo, expected_message",
    [
        pytest.param("core", "Passed:", id="Core integrations"),
        pytest.param("extras", "Passed:", id="Extras integrations"),
        pytest.param(
            "marketplace",
            "OpenMetrics validations is only enabled for core or extras integrations",
            id="Marketplace integrations",
        ),
    ],
)
def test_openmetrics_validate_repo(repo, expected_message, ddev, helpers, config_file):
    config_file.model.repo = repo
    config_file.save()

    result = ddev("validate", "openmetrics")

    assert expected_message in helpers.remove_trailing_spaces(result.output)
