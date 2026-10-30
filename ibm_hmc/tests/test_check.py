# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import io
import time
from unittest.mock import patch

import paramiko
import pytest

from datadog_checks.base import AgentCheck
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

# Same as above for an HMC whose version cannot be parsed: the check falls back
# to version 700, so only the base LPAR fields and shared_cycles_while_active exist.
SUBSYSTEM_VALUES_V700 = dict(SUBSYSTEM_VALUES, lpar='lparA,0.5,1,cap,13487973395246,353524992184,93964052971,0')


class FakeSSHClient:
    """Stands in for `paramiko.SSHClient` and answers HMC commands with fixtures.

    `lslparutil` samples are generated relative to the current time so that the
    check's "newer than last collection" filtering sees them, unlike a real HMC
    whose timestamps would be far in the past.
    """

    def __init__(
        self,
        lshmc_output=LSHMC_OUTPUT,
        servers=SERVERS,
        sample_rates=None,
        subsystem_values=SUBSYSTEM_VALUES,
        num_samples=3,
    ):
        self.lshmc_output = lshmc_output
        self.servers = servers
        self.sample_rates = (
            sample_rates if sample_rates is not None else {server.split(',')[0]: SAMPLE_RATE for server in servers}
        )
        self.subsystem_values = subsystem_values
        self.num_samples = num_samples
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
        return None, io.BytesIO(self._output_for(cmd).encode('utf-8')), io.BytesIO(b'')

    def _output_for(self, cmd):
        if cmd == 'lshmc -v':
            return self.lshmc_output
        if cmd.startswith('lssyscfg -r sys'):
            return '\n'.join(self.servers) + '\n'
        if cmd.startswith('lslparutil -r config'):
            server = self._server_of(cmd)
            return f'{self.sample_rates[server]}\n'
        for resource, values in self.subsystem_values.items():
            if cmd.startswith(f'lslparutil -r {resource} '):
                return self._samples(values)
        if cmd == 'cat /proc/meminfo':
            return MEMINFO_OUTPUT
        if cmd == 'monhmc -r swap -n 0':
            return SWAP_OUTPUT + '\n'
        return ''

    def _server_of(self, cmd):
        for server in self.sample_rates:
            if f'-m {server} ' in cmd or cmd.endswith(f'-m {server}'):
                return server
        raise AssertionError(f'Unknown server for command: {cmd}')

    def _samples(self, values):
        # Newest sample first, like the real lslparutil. The last two lines are
        # malformed on purpose: a truncated row and an unparsable timestamp.
        lines = ['truncated', '13/45/2018 99:99:99,' + values]
        for i in range(self.num_samples):
            when = time.strftime(IbmHmcCheck.SAMPLE_TIME_FORMAT, time.localtime(time.time() - (i + 1) * SAMPLE_RATE))
            lines.append(f'{when},{values}')
        return '\n'.join(lines) + '\n'


def run_check(dd_run_check, check, fake_client):
    with patch.object(paramiko, 'SSHClient', return_value=fake_client):
        dd_run_check(check)


def test_check_runs(aggregator, dd_run_check, instance):
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient()
    run_check(dd_run_check, check, fake)

    # Service check
    aggregator.assert_service_check(
        'ibm_hmc.can_connect', status=AgentCheck.OK, tags=['hmc-instance:hmc.example.com-22']
    )

    # Managed system metrics: one set per server, tagged with the LPAR sample's tag fields
    lpar_tags = ['server:ServerA', 'lpar_name:lparA', 'curr_sharing_mode:cap', 'mem_mode:ded']
    lpar_tags_b = [tag.replace('ServerA', 'ServerB') for tag in lpar_tags]
    aggregator.assert_metric('ibm_hmc.lpar.curr_proc_units', value=0.5, tags=lpar_tags)
    aggregator.assert_metric('ibm_hmc.lpar.curr_proc_units', value=0.5, tags=lpar_tags_b)
    aggregator.assert_metric('ibm_hmc.lpar.idle_cycles', value=0, tags=lpar_tags)
    aggregator.assert_metric('ibm_hmc.pool.total_pool_cycles', value=2538167299223, tags=['server:ServerA'])
    assert len(aggregator.metrics('ibm_hmc.pool.total_pool_cycles')) == 2
    aggregator.assert_metric('ibm_hmc.procpool.utilized_pool_cycles', value=467439053292, tags=['server:ServerA'])
    aggregator.assert_metric('ibm_hmc.mempool.sys_firmware_pool_mem', value=282, tags=['server:ServerA'])
    aggregator.assert_metric('ibm_hmc.sys.curr_avail_sys_mem', value=37376, tags=['server:ServerA'])

    # HMC appliance metrics
    appliance_tags = ['hmc-instance:hmc.example.com-22']
    aggregator.assert_metric('ibm_hmc.system.memory.memtotal', value=4128368, tags=appliance_tags)
    aggregator.assert_metric('ibm_hmc.system.memory.active_anon', value=65536, tags=appliance_tags)
    aggregator.assert_metric('ibm_hmc.system.memory.swaptotal', value=2040244, tags=appliance_tags)
    aggregator.assert_metric('ibm_hmc.system.memory.swap.total', value=2040244, tags=appliance_tags)
    aggregator.assert_metric('ibm_hmc.system.memory.swap.used', value=266000, tags=appliance_tags)

    # The lslparutil command resumes from the collection window, not the last sample
    sample_cmd = next(cmd for cmd in fake.commands if cmd.startswith('lslparutil -r lpar '))
    assert '--startyear' in sample_cmd
    assert '--filter "event_types=sample"' in sample_cmd


def test_sampling_throttled_by_sample_rate(aggregator, dd_run_check, instance):
    """A second collection within the HMC sample rate does not re-query subsystems."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(num_samples=1)
    run_check(dd_run_check, check, fake)
    run_check(dd_run_check, check, fake)

    # LPAR metrics were submitted once, appliance memory metrics on every run
    aggregator.assert_metric('ibm_hmc.lpar.curr_proc_units', count=2)  # one per server, first run only
    assert len(aggregator.metrics('ibm_hmc.system.memory.memtotal')) == 2  # both runs


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

    lpar_tags = ['server:ServerA', 'lpar_name:lparA', 'curr_sharing_mode:cap', 'mem_mode:ded']
    aggregator.assert_metric('ibm_hmc.lpar.shared_cycles_while_active', tags=lpar_tags)
    aggregator.assert_metric('ibm_hmc.lpar.curr_mem', value=2048, tags=lpar_tags)
    aggregator.assert_metric('ibm_hmc.lpar.idle_cycles', value=0, tags=lpar_tags)


def test_server_without_sample_rate_is_skipped(aggregator, dd_run_check, instance):
    """A server whose sample rate cannot be read is skipped for this run."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(sample_rates={'ServerA': SAMPLE_RATE, 'ServerB': 'not a number'})
    run_check(dd_run_check, check, fake)

    lpar_tags = ['server:ServerA', 'lpar_name:lparA', 'curr_sharing_mode:cap', 'mem_mode:ded']
    aggregator.assert_metric('ibm_hmc.lpar.curr_proc_units', tags=lpar_tags)
    # Only ServerA reports; nothing at all for ServerB
    assert len(aggregator.metrics('ibm_hmc.pool.total_pool_cycles')) == 1
    assert len(aggregator.metrics('ibm_hmc.system.memory.memtotal')) == 1


def test_connection_failure(aggregator, dd_run_check, instance):
    """A failed SSH connection raises and reports a CRITICAL service check."""

    class UnreachableClient(FakeSSHClient):
        def connect(self, host, port=22, username=None, password=None, **kwargs):
            raise paramiko.AuthenticationException('Authentication failed.')

    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    with pytest.raises(Exception, match='Authentication failed'):
        run_check(dd_run_check, check, UnreachableClient())

    aggregator.assert_service_check('ibm_hmc.can_connect', status=AgentCheck.CRITICAL)
    assert len(aggregator.metrics('ibm_hmc.system.memory.memtotal')) == 0
