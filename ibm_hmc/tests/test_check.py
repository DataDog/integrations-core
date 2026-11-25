# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import io
import time
from types import SimpleNamespace
from unittest.mock import patch

import paramiko
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
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

# One /proc/meminfo line per collected field (see MEMINFO_FIELDS), with kB values.
MEMINFO_OUTPUT = """\
MemTotal:       4128368 kB
MemFree:         161392 kB
Buffers:         397776 kB
Cached:         1457064 kB
SwapTotal:       2040244 kB
SwapFree:        1774244 kB
Active:          921600 kB
Inactive:        524288 kB
Active(anon):     65536 kB
Inactive(anon):   32768 kB
Active(file):    856064 kB
Inactive(file):  491520 kB
AnonPages:       131072 kB
Mapped:           65536 kB
Shmem:            16384 kB
Slab:            131072 kB
PageTables:       20480 kB
CommitLimit:     4128368 kB
Committed_AS:    2097152 kB
Dirty:             1024 kB
Writeback:           512 kB
VmallocUsed:      40960 kB
AnonHugePages:         0 kB
"""

SWAP_OUTPUT = 'Swap: 2040244k total, 266000k used, 1774244k free, 2282460k cached'

# One row of values per lslparutil resource, matching the fields the check
# requests for an HMC version of 884 (8.8.4): all optional LPAR fields included.
# Cycle values are cumulative counters on a real HMC; the first field of every
# row is the series identifier.
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
        raw_outputs=None,
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
        self.raw_outputs = raw_outputs or {}
        self.commands = []
        self.connect_calls = []
        self.exec_calls = []
        self.generated_times = {}

    # paramiko.SSHClient interface

    def connect(self, host, port=22, username=None, password=None, **kwargs):
        self.connect_calls.append(dict(port=port, username=username, password=password, **kwargs))

    def close(self):
        pass

    def set_missing_host_key_policy(self, policy):
        pass

    def load_system_host_keys(self, filename=None):
        self.known_hosts_file = filename

    def exec_command(self, cmd, environment=None, **kwargs):
        self.commands.append(cmd)
        self.exec_calls.append((cmd, kwargs))
        output = self._output_for(cmd)
        status = 1 if any(cmd.startswith(prefix) for prefix in self.failing_commands) else 0
        return None, FakeStdout(output.encode('utf-8'), status), io.BytesIO(b'')

    def _output_for(self, cmd):
        for prefix, output in self.raw_outputs.items():
            if cmd.startswith(prefix):
                return output
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
                return self._samples(resource, values)
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
            if (
                f'-m {server} ' in cmd
                or cmd.endswith(f'-m {server}')
                or f"-m '{server}' " in cmd
                or cmd.endswith(f"-m '{server}'")
            ):
                return server
        raise AssertionError(f'Unknown server for command: {cmd}')

    def _samples(self, resource, values):
        # Newest sample first, like the real lslparutil. The last two lines are
        # malformed on purpose: a truncated row and an unparsable timestamp.
        rows = values if isinstance(values, (list, tuple)) else [values]
        lines = ['truncated', '13/45/2018 99:99:99,' + rows[0]]
        timestamps = []
        for i in range(self.num_samples):
            when = self._format_hmc_time(self._hmc_now() - (i + 1) * SAMPLE_RATE)
            timestamps.append(when)
            lines.extend(f'{when},{row}' for row in rows)
        self.generated_times.setdefault(resource, []).extend(timestamps)
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

    # Commands and connection are bounded by the configured timeout
    assert fake.connect_calls[0]['timeout'] == 10
    assert all(kwargs.get('timeout') == 10 for _, kwargs in fake.exec_calls)

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
    aggregator.assert_metric('ibm_hmc.system.memory.swap.total', value=2040244, tags=BASE_TAGS)

    # Everything submitted matches metadata.csv, in type and in both directions
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), check_symmetric_inclusion=True, check_submission_type=True
    )


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
        'ibm_hmc.lpar.curr_proc_units',
        value=2.0,
        tags=lpar_tags(lpar='lparB', sharing_mode='uncap', mem_mode='shared'),
    )
    aggregator.assert_metric(
        'ibm_hmc.lpar.idle_cycles',
        value=42,
        tags=lpar_tags(lpar='lparB', sharing_mode='uncap', mem_mode='shared'),
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


def test_resumes_from_last_sample(aggregator, dd_run_check, instance):
    """A second collection resumes from the newest sample time and only submits new samples."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(sample_rates={'ServerA': 1, 'ServerB': 1}, num_samples=1)
    run_check(dd_run_check, check, fake)
    first_run_newest = max(time.strptime(when, IbmHmcCheck.SAMPLE_TIME_FORMAT) for when in fake.generated_times['lpar'])
    fake.commands.clear()
    time.sleep(1.1)  # let the per-server sample rate of 1 second elapse
    run_check(dd_run_check, check, fake)

    # The second query starts at the newest sample collected by the first run
    cmd = next(c for c in fake.commands if c.startswith('lslparutil -r lpar ') and '-m ServerA ' in c)
    assert f'--startyear {first_run_newest.tm_year}' in cmd
    assert f'--startmonth {first_run_newest.tm_mon}' in cmd
    assert f'--startday {first_run_newest.tm_mday}' in cmd
    assert f'--starthour {first_run_newest.tm_hour}' in cmd
    assert f'--startminute {first_run_newest.tm_min}' in cmd
    # Both runs submitted one sample per server, and nothing twice
    assert len(aggregator.metrics('ibm_hmc.lpar.curr_proc_units')) == 4


def test_sampling_disabled(aggregator, dd_run_check, instance, caplog):
    """A managed system with utilization sampling disabled (sample rate 0) is skipped with a warning."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(sample_rates={'ServerA': 0, 'ServerB': 60})
    run_check(dd_run_check, check, fake)

    assert not any('-F time,' in cmd and '-m ServerA ' in cmd for cmd in fake.commands)
    assert len(aggregator.metrics('ibm_hmc.lpar.curr_proc_units')) == 1  # ServerB only
    assert 'Utilization sampling is disabled' in caplog.text
    aggregator.assert_metric('ibm_hmc.can_connect', value=1, tags=BASE_TAGS)


def test_managed_system_name_with_space(aggregator, dd_run_check, instance):
    """Managed system names are quoted in the commands the HMC runs through its shell."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(servers=('Server A,9119-MHE,1001CFD',))
    run_check(dd_run_check, check, fake)

    sample_cmd = next(c for c in fake.commands if '-F time,' in c)
    assert "-m 'Server A'" in sample_cmd
    rate_cmd = next(c for c in fake.commands if c.startswith('lslparutil -r config'))
    assert "-m 'Server A'" in rate_cmd


def test_malformed_samples_warn(aggregator, dd_run_check, instance, caplog):
    """Rows that all fail to parse surface a warning instead of silently dropping the subsystem."""
    check = IbmHmcCheck('ibm_hmc', {}, [instance])
    fake = FakeSSHClient(raw_outputs={'lslparutil -r lpar': '12/13/2026 10:00:00,x,y'})
    run_check(dd_run_check, check, fake)

    assert len(aggregator.metrics('ibm_hmc.lpar.curr_proc_units')) == 0
    assert 'malformed LPAR samples' in caplog.text


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
    # A sample rate of 1 second lets the second run query without sleeping for a minute
    fake = FakeSSHClient(sample_rates={'ServerA': 1, 'ServerB': 1})
    run_check(dd_run_check, check, fake)
    first_run_samples = [cmd for cmd in fake.commands if '-F time,' in cmd]
    fake.commands.clear()
    # The failed attempt must also return an empty listing: a non-empty one would
    # keep the inventory even without the exit status guard
    fake.servers = ()
    fake.failing_commands = ('lssyscfg -r sys',)
    time.sleep(1.1)
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


@pytest.mark.parametrize('key_type,paramiko_key', [('rsa', paramiko.RSAKey), ('ecdsa', paramiko.ECDSAKey)])
def test_private_key_auth(aggregator, dd_run_check, instance, key_type, paramiko_key):
    """The configured key is loaded and sent as pkey, with the password as its passphrase."""
    config = {
        **instance,
        'private_key_file': '/keys/id_' + key_type,
        'private_key_type': key_type,
        'password': 'hunter2',
    }
    check = IbmHmcCheck('ibm_hmc', {}, [config])
    fake = FakeSSHClient()
    key = object()
    with patch.object(paramiko_key, 'from_private_key_file', return_value=key) as load:
        run_check(dd_run_check, check, fake)

    load.assert_called_once_with('/keys/id_' + key_type, password='hunter2')
    assert fake.connect_calls[0]['pkey'] is key
    assert fake.connect_calls[0]['passphrase'] == 'hunter2'


def test_private_key_failure_falls_back_to_password(aggregator, dd_run_check, instance, caplog):
    """An unreadable key file warns and the connection falls back to password auth."""
    config = {**instance, 'private_key_file': '/keys/missing', 'password': 'hunter2'}
    check = IbmHmcCheck('ibm_hmc', {}, [config])
    fake = FakeSSHClient()
    with patch.object(paramiko.RSAKey, 'from_private_key_file', side_effect=IOError('nope')):
        run_check(dd_run_check, check, fake)

    assert 'Unable to find private key file' in caplog.text
    assert fake.connect_calls[0]['password'] == 'hunter2'
    assert 'pkey' not in fake.connect_calls[0]


def test_force_sha1(aggregator, dd_run_check, instance):
    """force_sha1 disables the SHA2 pubkeys on the SSH client."""
    config = {**instance, 'force_sha1': True}
    check = IbmHmcCheck('ibm_hmc', {}, [config])
    fake = FakeSSHClient()
    run_check(dd_run_check, check, fake)

    assert fake.connect_calls[0]['disabled_algorithms'] == {'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']}


def test_known_hosts_file(aggregator, dd_run_check, instance):
    """A custom known hosts file is used for host key verification."""
    config = {**instance, 'known_hosts_file': '/path/known_hosts'}
    check = IbmHmcCheck('ibm_hmc', {}, [config])
    fake = FakeSSHClient()
    run_check(dd_run_check, check, fake)

    assert fake.known_hosts_file == '/path/known_hosts'


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
