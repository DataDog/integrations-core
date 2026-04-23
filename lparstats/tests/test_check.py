# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import patch

from datadog_checks.lparstats import LPARStats

MEMORY_OUTPUT = """\

System configuration: lcpu=8 mem=4096MB mpsz=0.00GB iome=4096.00MB iomp=9 ent=0.20

physb   hpi  hpit  pmem  iomin   iomu   iomf  iohwm iomaf %entc  vcsw
----- ----- ----- ----- ------ ------ ------ ------ ----- ----- -----
 1.20     0     0  4.00   62.2   -     -     -       0  15.2   427
"""

SPURR_OUTPUT = """\

System configuration: type=Shared mode=Uncapped smt=4 lcpu=8 mem=4096MB ent=0.20 Power=Disabled

Physical Processor Utilisation:

 --------Actual--------              ------Normalised------
 user   sys  wait  idle      freq    user   sys  wait  idle
 ----  ----  ----  ----   ---------  ----  ----  ----  ----
0.015 0.012 0.000 0.172 3.5GHz[100%] 0.015 0.012 0.000 0.172
"""


def _mock_run_cmd(cmd, sudo=False, timeout=None):
    if '-m' in cmd:
        return MEMORY_OUTPUT, '', 0
    if '-E' in cmd:
        return SPURR_OUTPUT, '', 0
    return '', '', 0


def test_check_runs(aggregator, instance):
    check = LPARStats('lparstats', {}, [instance])
    with patch('datadog_checks.lparstats.lparstats._run_cmd', side_effect=_mock_run_cmd):
        check.check(instance)

    # Memory metrics
    aggregator.assert_metric('system.lpar.memory.physb', value=1.20)
    aggregator.assert_metric('system.lpar.memory.entc', value=15.2)

    # SPURR metrics
    aggregator.assert_metric('system.lpar.spurr.user', value=0.015)
    aggregator.assert_metric('system.lpar.spurr.idle', value=0.172)
    aggregator.assert_metric('system.lpar.spurr.user.pct')

    # Verify at least one metric was collected for each category
    assert len(aggregator.metrics('system.lpar.memory.physb')) > 0
    assert len(aggregator.metrics('system.lpar.spurr.user')) > 0


def test_memory_output_too_short(aggregator, instance):
    check = LPARStats('lparstats', {}, [instance])
    with patch('datadog_checks.lparstats.lparstats._run_cmd', return_value=('', '', 0)):
        check.check(instance)
    # No metrics should be emitted for empty output
    assert len(aggregator.metrics('system.lpar.memory.physb')) == 0


def test_spurr_zero_total(aggregator, instance):
    """SPURR pct metrics should not be emitted when total is 0 (avoid div-by-zero)."""
    zero_spurr = """\

System configuration: ...

Physical Processor Utilisation:

 --------Actual--------              ------Normalised------
 user   sys  wait  idle      freq    user   sys  wait  idle
 ----  ----  ----  ----   ---------  ----  ----  ----  ----
0.000 0.000 0.000 0.000 3.5GHz[100%] 0.000 0.000 0.000 0.000
"""
    check = LPARStats('lparstats', {}, [instance])
    with patch(
        'datadog_checks.lparstats.lparstats._run_cmd',
        side_effect=lambda cmd, **kw: (zero_spurr, '', 0) if '-E' in cmd else ('', '', 0),
    ):
        check.check(instance)
    # .pct metrics should not be emitted when total is 0
    assert len(aggregator.metrics('system.lpar.spurr.user.pct')) == 0
