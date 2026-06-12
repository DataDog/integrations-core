# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock, patch

from datadog_checks.base import AgentCheck
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

HYPERVISOR_OUTPUT = """\

System configuration: lcpu=8 mem=4096MB ent=0.20

Hypervisor calls:
      Call  N_calls  spent.total  spent.hyp  call.avg  call.max
      -----  -------  -----------  ---------  --------  --------
      mmap    12345       2.50       0.80       0.002     0.010
"""

ENTITLEMENTS_OUTPUT = """\

System configuration: lcpu=8 mem=4096MB ent=0.20

I/O Memory Entitlement:
                        per pool
-----  -----  -----  ----  -----  -----  -----
  iompn  iodes  iomin  iomu  iomaf  iohwm  iores
     P1   16.0    8.0  10.0    0.0   12.0   16.0
"""


def _make_proc(stdout=''):
    proc = MagicMock()
    proc.stdout = stdout.encode('utf-8')
    proc.stderr = b''
    proc.returncode = 0
    return proc


def _mock_subprocess_run(cmd, **kwargs):
    if '-m' in cmd and '-eR' not in cmd:
        return _make_proc(MEMORY_OUTPUT)
    if '-E' in cmd:
        return _make_proc(SPURR_OUTPUT)
    if '-H' in cmd:
        return _make_proc(HYPERVISOR_OUTPUT)
    if '-eR' in cmd:
        return _make_proc(ENTITLEMENTS_OUTPUT)
    return _make_proc()


def test_check_runs(aggregator, dd_run_check, instance):
    check = LPARStats('lparstats', {}, [instance])
    with patch('datadog_checks.lparstats.lparstats.subprocess.run', side_effect=_mock_subprocess_run):
        dd_run_check(check)

    # Memory metrics (no tags expected)
    aggregator.assert_metric('system.lpar.memory.physb', value=1.20, tags=[])
    aggregator.assert_metric('system.lpar.memory.entc', value=15.2, tags=[])

    # SPURR metrics (no tags expected)
    aggregator.assert_metric('system.lpar.spurr.user', value=0.015, tags=[])
    aggregator.assert_metric('system.lpar.spurr.idle', value=0.172, tags=[])
    aggregator.assert_metric('system.lpar.spurr.user.pct', tags=[])

    aggregator.assert_service_check('lparstats.can_collect', status=AgentCheck.OK)


def test_lparstat_command_failure(aggregator, instance):
    """Service check is CRITICAL when lparstat exits non-zero."""
    check = LPARStats('lparstats', {}, [instance])
    failed_proc = _make_proc('')
    failed_proc.returncode = 1
    with patch('datadog_checks.lparstats.lparstats.subprocess.run', return_value=failed_proc):
        check.check(instance)
    aggregator.assert_service_check('lparstats.can_collect', status=AgentCheck.CRITICAL)
    assert len(aggregator.metrics('system.lpar.memory.physb')) == 0


def test_hypervisor_and_entitlements(aggregator, dd_run_check):
    """Hypervisor and memory-entitlement collectors emit metrics with call/iompn tags."""
    inst = {
        'name': 'lparstats',
        'memory_stats': False,
        'page_stats': False,
        'memory_entitlements': True,
        'hypervisor': True,
        'spurr_utilization': False,
        'sudo': True,  # makes root=True so both collectors are activated
    }
    check = LPARStats('lparstats', {}, [inst])
    with patch('datadog_checks.lparstats.lparstats.subprocess.run', side_effect=_mock_subprocess_run):
        dd_run_check(check)

    aggregator.assert_metric('system.lpar.hypervisor.n_calls', value=12345.0, tags=['call:mmap'])
    aggregator.assert_metric('system.lpar.hypervisor.time.spent.total', value=2.50, tags=['call:mmap'])
    aggregator.assert_metric('system.lpar.memory.entitlement.iodes', value=16.0, tags=['iompn:P1'])
    aggregator.assert_metric('system.lpar.memory.entitlement.iomin', value=8.0, tags=['iompn:P1'])


def test_memory_output_too_short(aggregator, instance):
    check = LPARStats('lparstats', {}, [instance])
    with patch('datadog_checks.lparstats.lparstats.subprocess.run', return_value=_make_proc('')):
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
        'datadog_checks.lparstats.lparstats.subprocess.run',
        side_effect=lambda cmd, **kw: _make_proc(zero_spurr) if '-E' in cmd else _make_proc(''),
    ):
        check.check(instance)
    # .pct metrics should not be emitted when total is 0
    assert len(aggregator.metrics('system.lpar.spurr.user.pct')) == 0
