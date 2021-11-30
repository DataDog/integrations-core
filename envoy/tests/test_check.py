from .common import DEFAULT_INSTANCE, requires_new_environment
import pytest

pytestmark = [requires_new_environment]

@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, dd_run_check, check):
    dd_run_check(check(DEFAULT_INSTANCE))

    for metric in []:
        aggregator.assert_metric('envoy.{}'.format(metric))

    aggregator.assert_all_metrics_covered()
