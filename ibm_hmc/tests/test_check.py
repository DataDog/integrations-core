# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import io
import time
from types import SimpleNamespace
from unittest.mock import patch

import paramiko
import pytest

from datadog_checks.ibm_hmc import IbmHmcCheck

LSHMC_OUTPUT = """\
vpd=*FC ????????
*VC 20.0
*N2 Wed Aug 26 08:13:14 CDT 2015
*FC ????????
*DS Hardware Management Console
*TM 7042-CR7
*SE 10DA45C
*MN IBM
*PN 42D01T
*SZ 8363966464
*OS Embedded Operating Systems
*NA 9.3.242.97
*FC ????????
*DS Platform Firmware
*RM V8R8.4.0.0
"""

SERVERS = (
    'ServerA,9119-MHE,1001CFD',
    'ServerB,9119-MHE,1002CFD',
)

SAMPLE_RATE = 60

MEMINFO_OUTPUT = """\
MemTotal:      4128368 kB
MemFree:        161392 kB
Buffers:        397776 kB
Cached:        1457064 kB
Active(anon):    65536 kB
SwapTotal:      2040244 kB
SwapFree:       1774244 kB
"""

SWAP_OUTPUT = 'Swap: 2040244k total, 266000k used, 1774244k free, 2282460k cached'

# One row of values per lslparutil resource, matching the fields the check
# requests for an HMC version of 884 (8.8.4): all optional LPAR fields included.
SUBSYSTEM_VALUES = {
    'lpar': 'lparA,0.5,1,cap,13487973395246,353524992184,93964052971,0,ded,2048,2048,96,128,10,0',
    'pool': '2538167299223,187829506335722,3.00,1.00,1.10',
    'procpool': '1001,134967149091025,467439053292',
    'mempool': '24576,308,24,34816,282',
    'sys': '37376,65536,1546',
}

# A second concurrent LPAR and shared processor pool, to exercise per-series sampling.
LPAR_ROW_B = 'lparB,2.0,4,uncap,24487973395246,453524992184,103964052971,0,shared,4096,4096,96,128,10,42'
PROCPOOL_ROW_B = '1002,234967149091025,567439053292'

# Same as the default set for an HMC whose version cannot be parsed: the check falls back
# to version 7.0, so only the base LPAR fields and shared_cycles_while_active exist.
SUBSYSTEM_VALUES_V700 = dict(SUBSYSTEM_VALUES, lpar='lparA,0.5,1,cap,13487973395246,353524992184,93964052971,0')


class FakeStdout(io.BytesIO):
    """A stdout file object with the paramiko channel API the exit status is read from."""

    def __init__(self, data, status=0):
        super().__init__(data)
        self.channel = SimpleNamespace(recv_exit_status=lambda: status)


class FakeSSHClient:
    """Stands in for `paramiko.SSHClient` and answers HMC commands with fixtures.

    `lslparutil` samples are generated relative to the (configurable) HMC clock so
    that the check's "newer than last collection" filtering sees them, unlike a real
    HMC whose timestamps would be far in the past. Subsystem values may be a list of
    rows, producing one row per series and timestamp like the real command.
    """

    def __init__(
        self,
        lshmc_output=LSHMC_OUTPUT,
        servers=SERVERS,
        sample_rates=None,
        subsystem_values=SUBSYSTEM_VALUES,
        num_samples=3,
        failing_commands=(),
        hmc_clock_offset=0.0,
    ):
        self.lshmc_output = lshmc_output
        self.servers = servers
        self.sample_rates = (
            sample_rates if sample_rates is not None else {server.split(',')[0]: SAMPLE_RATE for server in servers}
        )
        self.subsystem_values = subsystem_values
        self.num_samples = num_samples
        self.failing_commands = failing_commands
        self.hmc_clock_offset = hmc_clock_offset
        self.commands = []

    # paramiko.SSHClient interface

    def connect(self, host, port=22, username=None, password=None, **kwargs):
        pass

    def close(self):
        pass

    def set_missing_host_key_policy(self, policy):
        pass

    def load_system_host_keys(self):
        pass

    def exec_command(self, cmd, environment=None, **kwargs):
        self.commands.append(cmd)
        output = self._output_for(cmd)
        status = 1 if any(cmd.startswith(prefix) for prefix in self.failing_commands) else 0
        return None, FakeStdout(output.encode('utf-8'), status), io.BytesIO(b'')

    def _output_for(self, cmd):
        if cmd == 'lshmc -v':
            return self.lshmc_output
        if cmd.startswith('lssyscfg -r sys'):
            return '\n'.join(self.servers) + '\n'
        if cmd.startswith('lslparutil -r config'):
            return f'{self.sample_rates[self._server_of(cmd)]}\n'
        if cmd == IbmHmcCheck.GET_TIME_CMD:
            return self._format_hmc_time(self._hmc_now()) + '\n'
        for resource, values in self.subsystem_values.items():
            if cmd.startswith(f'lslparutil -r {resource} '):
                return self._samples(values)
        if cmd == 'cat /proc/meminfo':
            return MEMINFO_OUTPUT
        if cmd == 'monhmc -r swap -n 0':
            return SWAP_OUTPUT + '\n'
        return ''

    def _hmc_now(self):
        return time.time() + self.hmc_clock_offset

    def _format_hmc_time(self, timestamp):
        return time.strftime(IbmHmcCheck.SAMPLE_TIME_FORMAT, time.localtime(timestamp))

    def _server_of(self, cmd):
        for server in self.sample_rates:
            if f'-m {server} ' in cmd or cmd.endswith(f'-m {server}'):
                return server
        raise AssertionError(f'Unknown server for command: {cmd}')

    def _samples(self, values):
        # Newest sample first, like the real lslparutil. The last two lines are
        # malformed on purpose: a truncated row and an unparsable timestamp.
        rows = values if isinstance(values, (list, tuple)) else [values]
        lines = ['truncated', '13/45/2018 99:99:99,' + rows[0]]
        for i in range(self.num_samples):
            when = self._format_hmc_time(self._hmc_now() - (i + 1) * SAMPLE_RATE)
            lines.extend(f'{when},{row}' for row in rows)
        return '\n'.join(lines) + '\n'


def run_check(dd_run_check, check, fake_client):
    with patch.object(paramiko, 'SSHClient', return_value=fake_client):
        dd_run_check(check)


BASE_TAGS = ['hmc-instance:hmc.example.com-22']


def lpar_tags(server='ServerA', lpar='lparA', sharing_mode='cap', mem_mode='ded'):
    return [
        *BASE_TAGS,
        f'server:{server}',
        f'lpar_name:{lpar}',
        f'curr_sharing_mode:{sharing_mode}',
        f'mem_mode:{mem_mode}',
    ]


def server_tags(server='ServerA'):
    return [*BASE_TAGS, f'server:{server}']


def test_check_runs(aggregator, dd_run_check, instance):
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient()
    run_check(dd_run_check, check, fake)

    # Connectivity is reported as a metric, not a service check
    aggregator.assert_metric('ibm_hmc.can_connect', value=1, tags=BASE_TAGS)
    assert len(aggregator.service_checks('ibm_hmc.can_connect')) == 0

    # Managed system metrics: one set per server, tagged with the instance tags and
    # the LPAR sample's series fields
    aggregator.assert_metric('ibm_hmc.lpar.curr_proc_units', value=0.5, tags=lpar_tags())
    aggregator.assert_metric('ibm_hmc.lpar.curr_proc_units', value=0.5, tags=lpar_tags(server='ServerB'))
    aggregator.assert_metric('ibm_hmc.lpar.idle_cycles', value=0, tags=lpar_tags())
    aggregator.assert_metric('ibm_hmc.pool.total_pool_cycles', value=2538167299223, tags=server_tags())
    assert len(aggregator.metrics('ibm_hmc.pool.total_pool_cycles')) == 2
    # The shared processor pool is identified by a tag, not a gauge
    aggregator.assert_metric(
        'ibm_hmc.procpool.utilized_pool_cycles',
        value=467439053292,
        tags=[*server_tags(), 'shared_proc_pool_id:1001'],
    )
    assert len(aggregator.metrics('ibm_hmc.procpool.shared_proc_pool_id')) == 0
    aggregator.assert_metric('ibm_hmc.mempool.sys_firmware_pool_mem', value=282, tags=server_tags())
    aggregator.assert_metric('ibm_hmc.sys.curr_avail_sys_mem', value=37376, tags=server_tags())

    # HMC appliance metrics
    aggregator.assert_metric('ibm_hmc.system.memory.memtotal', value=4128368, tags=BASE_TAGS)
    aggregator.assert_metric('ibm_hmc.system.memory.active_anon', value=65536, tags=BASE_TAGS)
    aggregator.assert_metric('ibm_hmc.system.memory.swaptotal', value=2040244, tags=BASE_TAGS)
    aggregator.assert_metric('ibm_hmc.system.memory.swap.total', value=2040244, tags=BASE_TAGS)
    aggregator.assert_metric('ibm_hmc.system.memory.swap.used', value=266000, tags=BASE_TAGS)

    # The lslparutil command resumes from the collection window, not the last sample
    sample_cmd = next(cmd for cmd in fake.commands if cmd.startswith('lslparutil -r lpar '))
    assert '--startyear' in sample_cmd
    assert '--filter "event_types=sample"' in sample_cmd


def test_multi_lpar_and_multi_pool(aggregator, dd_run_check, instance):
    """A managed system with several LPARs and pools reports every series, not only the newest row."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(
        subsystem_values={
            **SUBSYSTEM_VALUES,
            'lpar': [SUBSYSTEM_VALUES['lpar'], LPAR_ROW_B],
            'procpool': [SUBSYSTEM_VALUES['procpool'], PROCPOOL_ROW_B],
        }
    )
    run_check(dd_run_check, check, fake)

    aggregator.assert_metric('ibm_hmc.lpar.curr_proc_units', value=0.5, tags=lpar_tags())
    aggregator.assert_metric(
        'ibm_hmc.lpar.curr_proc_units', value=2.0, tags=lpar_tags(lpar='lparB', sharing_mode='uncap', mem_mode='shared')
    )
    aggregator.assert_metric(
        'ibm_hmc.lpar.idle_cycles', value=42, tags=lpar_tags(lpar='lparB', sharing_mode='uncap', mem_mode='shared')
    )
    aggregator.assert_metric(
        'ibm_hmc.procpool.utilized_pool_cycles',
        value=467439053292,
        tags=[*server_tags(), 'shared_proc_pool_id:1001'],
    )
    aggregator.assert_metric(
        'ibm_hmc.procpool.utilized_pool_cycles',
        value=567439053292,
        tags=[*server_tags(), 'shared_proc_pool_id:1002'],
    )


def test_sampling_throttled_by_sample_rate(aggregator, dd_run_check, instance):
    """A second collection within the HMC sample rate does not re-query subsystems."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(num_samples=1)
    run_check(dd_run_check, check, fake)
    run_check(dd_run_check, check, fake)

    # LPAR metrics were submitted once, appliance metrics on every run
    aggregator.assert_metric('ibm_hmc.lpar.curr_proc_units', count=2)  # one per server, first run only
    assert len(aggregator.metrics('ibm_hmc.system.memory.memtotal')) == 2  # both runs
    assert len(aggregator.metrics('ibm_hmc.can_connect')) == 2  # both runs


def test_version_fallback_disables_newer_fields(aggregator, dd_run_check, instance):
    """Without a parsable *RM line the check assumes HMC 7.0 and drops newer LPAR fields."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(
        lshmc_output='*DS Hardware Management Console\n',
        subsystem_values=SUBSYSTEM_VALUES_V700,
    )
    run_check(dd_run_check, check, fake)

    aggregator.assert_metric('ibm_hmc.lpar.shared_cycles_while_active', value=0)
    assert len(aggregator.metrics('ibm_hmc.lpar.curr_mem')) == 0
    assert len(aggregator.metrics('ibm_hmc.lpar.idle_cycles')) == 0


def test_hmc10_two_digit_major_version(aggregator, dd_run_check, instance):
    """HMC 10 releases have a two-digit major version and must collect all version-gated fields.

    Collapsing the version into a truncated integer turned `V10R3.1060.0` into 103,
    below every 7.x threshold, silently disabling all gated LPAR metrics on HMC 10.
    """
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(lshmc_output='*DS Hardware Management Console\n*RM V10R3.1060.0\n')
    run_check(dd_run_check, check, fake)

    aggregator.assert_metric('ibm_hmc.lpar.shared_cycles_while_active', tags=lpar_tags())
    aggregator.assert_metric('ibm_hmc.lpar.curr_mem', value=2048, tags=lpar_tags())
    aggregator.assert_metric('ibm_hmc.lpar.idle_cycles', value=0, tags=lpar_tags())


def test_bootstrap_uses_hmc_clock(aggregator, dd_run_check, instance):
    """The first collection window comes from the HMC's clock, not the Agent's.

    An Agent in a different time zone would otherwise request samples starting in
    the HMC's future, get empty results, and never start collecting.
    """
    offset = -5 * 3600
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(hmc_clock_offset=offset)
    before = time.localtime(time.time() + offset)
    run_check(dd_run_check, check, fake)
    after = time.localtime(time.time() + offset)

    sample_cmd = next(cmd for cmd in fake.commands if cmd.startswith('lslparutil -r lpar '))
    # Tolerate a minute boundary crossed between the check run and this assertion
    for prefix, field in (
        ('--startyear', 'tm_year'),
        ('--startmonth', 'tm_mon'),
        ('--startday', 'tm_mday'),
        ('--starthour', 'tm_hour'),
        ('--startminute', 'tm_min'),
    ):
        values = {getattr(before, field), getattr(after, field)}
        assert any(f'{prefix} {value}' in sample_cmd for value in values), prefix
    # Managed-system metrics were still collected
    aggregator.assert_metric('ibm_hmc.lpar.curr_proc_units', value=0.5, tags=lpar_tags())


def test_discovery_failure_keeps_inventory(aggregator, dd_run_check, instance):
    """A failed managed-server discovery keeps the known inventory instead of dropping it for an hour."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    check.SERVER_REFRESH_PERIOD = 0  # refresh on every run
    # A sample rate of 0 disables the per-subsystem throttling, so both runs sample
    fake = FakeSSHClient(sample_rates={'ServerA': 0, 'ServerB': 0})
    run_check(dd_run_check, check, fake)
    first_run_samples = [cmd for cmd in fake.commands if '-F time,' in cmd]
    fake.failing_commands = ('lssyscfg -r sys',)
    fake.commands.clear()
    run_check(dd_run_check, check, fake)

    # The second run still samples every known server: the failed discovery
    # did not wipe the inventory for an hour
    second_run_samples = [cmd for cmd in fake.commands if '-F time,' in cmd]
    assert len(second_run_samples) == len(first_run_samples)
    assert any('-m ServerA ' in cmd for cmd in second_run_samples)
    assert len(aggregator.metrics('ibm_hmc.can_connect')) == 2


def test_subsystem_command_failure(aggregator, dd_run_check, instance):
    """A failed lslparutil call skips that subsystem without aborting the others."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(failing_commands=('lslparutil -r procpool',))
    run_check(dd_run_check, check, fake)

    assert len(aggregator.metrics('ibm_hmc.procpool.total_pool_cycles')) == 0
    aggregator.assert_metric('ibm_hmc.pool.total_pool_cycles', value=2538167299223, tags=server_tags())
    aggregator.assert_metric('ibm_hmc.can_connect', value=1, tags=BASE_TAGS)


def test_server_without_sample_rate_is_skipped(aggregator, dd_run_check, instance):
    """A server whose sample rate cannot be read is skipped for this run."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(sample_rates={'ServerA': SAMPLE_RATE, 'ServerB': 'not a number'})
    run_check(dd_run_check, check, fake)

    aggregator.assert_metric('ibm_hmc.lpar.curr_proc_units', tags=lpar_tags())
    # Only ServerA reports; nothing at all for ServerB
    assert len(aggregator.metrics('ibm_hmc.pool.total_pool_cycles')) == 1
    assert len(aggregator.metrics('ibm_hmc.system.memory.memtotal')) == 1


def test_connection_failure(aggregator, dd_run_check, instance):
    """A failed SSH connection raises and reports can_connect as 0."""

    class UnreachableClient(FakeSSHClient):
        def connect(self, host, port=22, username=None, password=None, **kwargs):
            raise paramiko.AuthenticationException('Authentication failed.')

    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    with pytest.raises(Exception, match='Authentication failed'):
        run_check(dd_run_check, check, UnreachableClient())

    aggregator.assert_metric('ibm_hmc.can_connect', value=0, tags=BASE_TAGS)
    assert len(aggregator.metrics('ibm_hmc.system.memory.memtotal')) == 0
