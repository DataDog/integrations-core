# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import subprocess
from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest

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


ALL_COLLECTORS_INSTANCE = {
    'name': 'lparstats',
    'memory_stats': True,
    'page_stats': True,
    'memory_entitlements': True,
    'hypervisor': True,
    'spurr_utilization': True,
    'sudo': True,
}

# One metric each collector emits from its default output
COLLECTOR_METRICS = {
    'memory': 'system.lpar.memory.physb',
    'entitlements': 'system.lpar.memory.entitlement.iodes',
    'hypervisor': 'system.lpar.hypervisor.n_calls',
    'spurr': 'system.lpar.spurr.user',
}


def _make_proc(stdout: str = '', returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.stdout = stdout.encode('utf-8')
    proc.stderr = b'lparstat: error' if returncode else b''
    proc.returncode = returncode
    return proc


def _lparstat(
    memory: str | MagicMock = MEMORY_OUTPUT,
    entitlements: str | MagicMock = ENTITLEMENTS_OUTPUT,
    hypervisor: str | MagicMock = HYPERVISOR_OUTPUT,
    spurr: str | MagicMock = SPURR_OUTPUT,
) -> Callable[..., MagicMock]:
    """Build a `subprocess.run` replacement that answers each lparstat invocation with the given output.

    An output can be a string, or a process mock to control the return code.
    """

    def run(cmd: list[str], **kwargs: object) -> MagicMock:
        if '-eR' in cmd:
            output = entitlements
        elif '-m' in cmd:
            output = memory
        elif '-H' in cmd:
            output = hypervisor
        elif '-E' in cmd:
            output = spurr
        else:
            output = ''
        return output if isinstance(output, MagicMock) else _make_proc(output)

    return run


_mock_subprocess_run = _lparstat()


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


def test_non_root_warning_logged_once(aggregator, dd_run_check, instance, caplog):
    """The 'not running as root' notice is logged once per check instance, not every collection interval."""
    check = LPARStats('lparstats', {}, [instance])
    with (
        patch('datadog_checks.lparstats.lparstats.subprocess.run', side_effect=_mock_subprocess_run),
        patch('datadog_checks.lparstats.lparstats.os.getuid', return_value=12345),
        caplog.at_level(logging.INFO),
    ):
        dd_run_check(check)
        dd_run_check(check)

    assert caplog.text.count('Not running as root or sudo') == 1
    aggregator.assert_service_check('lparstats.can_collect', status=AgentCheck.OK)


def test_dash_values_skipped_silently(aggregator, dd_run_check, instance, caplog):
    """lparstat prints '-' for stats that do not apply to the LPAR; they are skipped without logging."""
    check = LPARStats('lparstats', {}, [instance])
    with patch('datadog_checks.lparstats.lparstats.subprocess.run', side_effect=_mock_subprocess_run):
        with caplog.at_level(logging.INFO):
            dd_run_check(check)

    assert 'unable to convert' not in caplog.text
    assert len(aggregator.metrics('system.lpar.memory.iomu')) == 0
    assert len(aggregator.metrics('system.lpar.memory.iomf')) == 0
    assert len(aggregator.metrics('system.lpar.memory.iohwm')) == 0
    # sibling fields are still collected
    aggregator.assert_metric('system.lpar.memory.physb', value=1.20, tags=[])
    aggregator.assert_metric('system.lpar.memory.entc', value=15.2, tags=[])


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


@pytest.mark.parametrize('collector', sorted(COLLECTOR_METRICS))
@pytest.mark.parametrize(
    'output',
    [pytest.param(_make_proc('', returncode=1), id='nonzero-exit'), pytest.param('', id='empty-output')],
)
def test_collector_failure_does_not_stop_other_collectors(aggregator, dd_run_check, collector, output):
    check = LPARStats('lparstats', {}, [ALL_COLLECTORS_INSTANCE])
    with patch('datadog_checks.lparstats.lparstats.subprocess.run', side_effect=_lparstat(**{collector: output})):
        dd_run_check(check)

    aggregator.assert_service_check('lparstats.can_collect', status=AgentCheck.CRITICAL)
    for name, metric in COLLECTOR_METRICS.items():
        aggregator.assert_metric(metric, count=0 if name == collector else 1)


@pytest.mark.parametrize(
    'error',
    [
        pytest.param(subprocess.TimeoutExpired('lparstat', 5), id='timeout'),
        pytest.param(FileNotFoundError('lparstat'), id='missing-binary'),
    ],
)
def test_lparstat_not_runnable(aggregator, dd_run_check, error):
    check = LPARStats('lparstats', {}, [ALL_COLLECTORS_INSTANCE])
    with patch('datadog_checks.lparstats.lparstats.subprocess.run', side_effect=error):
        dd_run_check(check)

    aggregator.assert_service_check('lparstats.can_collect', status=AgentCheck.CRITICAL)
    assert not aggregator.metric_names


@pytest.mark.parametrize(
    'collector, output, collected, skipped',
    [
        pytest.param(
            'memory',
            """\

System configuration: lcpu=8 mem=4096MB

physb   hpi  hpit  pmem
----- ----- ----- -----
 1.20  n/a     0
""",
            {'system.lpar.memory.physb': ([], 1.20), 'system.lpar.memory.hpit': ([], 0.0)},
            ['system.lpar.memory.hpi', 'system.lpar.memory.pmem'],
            id='memory',
        ),
        pytest.param(
            'hypervisor',
            """\

System configuration: lcpu=8 mem=4096MB ent=0.20

Hypervisor calls:
      Call  N_calls  spent.total  spent.hyp  call.avg  call.max
      -----  -------  -----------  ---------  --------  --------
      mmap    12345       -       n/a       0.002     0.010   99
      cede
""",
            {
                'system.lpar.hypervisor.n_calls': (['call:mmap'], 12345.0),
                'system.lpar.hypervisor.time.call.avg': (['call:mmap'], 0.002),
                'system.lpar.hypervisor.time.call.max': (['call:mmap'], 0.010),
            },
            ['system.lpar.hypervisor.time.spent.total', 'system.lpar.hypervisor.time.spent.hyp'],
            id='hypervisor',
        ),
        pytest.param(
            'entitlements',
            """\

System configuration: lcpu=8 mem=4096MB ent=0.20

I/O Memory Entitlement:
                        per pool
-----  -----  -----  ----  -----  -----  -----
  iompn  iodes  iomin  iomu  iomaf
     P1   16.0    -    n/a
     P2
""",
            {'system.lpar.memory.entitlement.iodes': (['iompn:P1'], 16.0)},
            [
                'system.lpar.memory.entitlement.iomin',
                'system.lpar.memory.entitlement.iomu',
                'system.lpar.memory.entitlement.iomaf',
            ],
            id='entitlements',
        ),
        pytest.param(
            'spurr',
            """\

System configuration: type=Shared mode=Uncapped smt=4 lcpu=8 mem=4096MB ent=0.20 Power=Disabled

Physical Processor Utilisation:

 --------Actual--------              ------Normalised------
 user   sys  wait  idle      freq    user   sys  wait  idle
 ----  ----  ----  ----   ---------  ----  ----  ----  ----
0.015    -  0.000 0.172 3.5GHz[100%] 0.015
""",
            {'system.lpar.spurr.user': ([], 0.015), 'system.lpar.spurr.user.norm': ([], 0.015)},
            ['system.lpar.spurr.sys', 'system.lpar.spurr.sys.norm'],
            id='spurr',
        ),
    ],
)
def test_unusable_values_are_skipped(aggregator, dd_run_check, collector, output, collected, skipped):
    """Missing, `-` and non-numeric values are skipped without dropping the other values of the row."""
    check = LPARStats('lparstats', {}, [ALL_COLLECTORS_INSTANCE])
    with patch('datadog_checks.lparstats.lparstats.subprocess.run', side_effect=_lparstat(**{collector: output})):
        dd_run_check(check)

    for metric, (tags, value) in collected.items():
        aggregator.assert_metric(metric, value=value, tags=tags)
    for metric in skipped:
        aggregator.assert_metric(metric, count=0)
    aggregator.assert_service_check('lparstats.can_collect', status=AgentCheck.OK)
