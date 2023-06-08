import pytest


@pytest.mark.parametrize(
    "check_name",
    [
        pytest.param("aerospike", id="Aerospike check.py OpenMetricsV2"),
        pytest.param("amazon_msk", id="Amazon MSK amazon_msk.py OpenMetricsV1 and V2"),
    ],
)
def test_openmetrics_pass_single_parameter(ddev, repository, check_name, helpers, network_replay):
    result = ddev("validate", "openmetrics", check_name)

    assert result.exit_code == 0, result.output

    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Validating default metric limit for OpenMetrics integrations ...
        OpenMetrics Metric limit

        Passed: 1
        """
    )


def test_openmetrics_fail_single_parameter(ddev, helpers, repository, network_replay):
    missing_metric_limit = '''
            class ArangodbCheck(OpenMetricsBaseCheckV2, ConfigMixin):
            __NAMESPACE__ = 'arangodb'
            def __init__(self, name, init_config, instances):
                super(ArangodbCheck, self).__init__(name, init_config, instances)
        '''

    check = "arangodb"
    check_file = repository.path / check / "datadog_checks" / check / "check.py"

    with open(check_file, "w") as f:
        f.write(missing_metric_limit)

    result = ddev("validate", "openmetrics", "arangodb")

    assert result.exit_code == 1, result.output

    assert "Errors: 1" in helpers.remove_trailing_spaces(result.output)


def test_openmetrics_skip_openmetrics(ddev, helpers, repository, network_replay):
    result = ddev("validate", "openmetrics", "openmetrics")

    assert result.exit_code == 0, result.output

    assert "Passed" not in helpers.remove_trailing_spaces(result.output)
    assert "Errors" not in helpers.remove_trailing_spaces(result.output)


@pytest.mark.parametrize(
    "repo, expected_message",
    [
        pytest.param("core", "Passed:", id="Core integrations"),
        pytest.param(
            "marketplace",
            "OpenMetrics validations is only enabled for core or extras integrations, skipping for repo marketplace",
            id="Marketplace integrations",
        ),
    ],
)
def test_openmetrics_validate_repo(repo, repository, expected_message, ddev, helpers, config_file):
    config_file.model.repo = repo
    config_file.save()

    result = ddev("validate", "openmetrics", "all")

    assert expected_message in helpers.remove_trailing_spaces(result.output)
