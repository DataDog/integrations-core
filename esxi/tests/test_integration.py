import pytest

from datadog_checks.esxi import EsxiCheck


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_esxi_metric_up(vcsim_instance, dd_run_check, aggregator):
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    dd_run_check(check)
    aggregator.assert_metric('esxi.host.can_connect', 1, count=1, tags=["esxi_url:127.0.0.1", "port:8989"])
