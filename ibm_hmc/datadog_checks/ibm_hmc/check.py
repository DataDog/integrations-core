# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
#
# Ported from datadog-unix-agent to integrations-core (Python 3, datadog_checks_base).
# Original: https://github.com/DataDog/datadog-unix-agent/tree/master/checks/bundled/hmc

from __future__ import annotations

import re
import time

import paramiko

from datadog_checks.base import AgentCheck

from .config_models import ConfigMixin

# Sample fields per `lslparutil` resource. Each entry is (field, is_gauge): fields
# with is_gauge=False are not metrics, their value identifies the sample's series
# and is attached as a tag to every metric of that sample instead.
SAMPLE_FIELDS: dict[str, tuple[tuple[str, bool], ...]] = {
    'LPAR': (
        ('lpar_name', False),
        ('curr_proc_units', True),
        ('curr_procs', True),
        ('curr_sharing_mode', False),
        ('entitled_cycles', True),
        ('capped_cycles', True),
        ('uncapped_cycles', True),
    ),
    'POOL': (
        ('total_pool_cycles', True),
        ('utilized_pool_cycles', True),
        ('configurable_pool_proc_units', True),
        ('borrowed_pool_proc_units', True),
        ('curr_avail_pool_proc_units', True),
    ),
    'PROCPOOL': (
        ('shared_proc_pool_id', False),
        ('total_pool_cycles', True),
        ('utilized_pool_cycles', True),
    ),
    'MEMPOOL': (
        ('curr_pool_mem', True),
        ('lpar_curr_io_entitled_mem', True),
        ('lpar_mapped_io_entitled_mem', True),
        ('lpar_run_mem', True),
        ('sys_firmware_pool_mem', True),
    ),
    'SYS': (
        ('curr_avail_sys_mem', True),
        ('configurable_sys_mem', True),
        ('sys_firmware_mem', True),
    ),
}

# LPAR fields that only exist from the given HMC version onward (7.0, 7.3.4, 7.7.2).
LPAR_EXTRA_FIELDS = (
    ((7, 0, 0), (('shared_cycles_while_active', True),)),
    (
        (7, 3, 4),
        (
            ('mem_mode', False),
            ('curr_mem', True),
            ('phys_run_mem', True),
            ('curr_io_entitled_mem', True),
            ('mapped_io_entitled_mem', True),
            ('mem_overage_cooperation', True),
        ),
    ),
    ((7, 7, 2), (('idle_cycles', True),)),
)


class ManagedServer:
    """A POWER system managed by the HMC, with per-subsystem sampling state."""

    def __init__(self, name: str, model: str, serial: str) -> None:
        self.name = name
        self.model = model
        self.serial = serial
        self.sample_rate: int | None = None
        # Local wall-clock time of the last collection per subsystem, used to
        # avoid querying a subsystem more often than the HMC's own sample rate.
        self.last_collection = dict.fromkeys(SAMPLE_FIELDS)
        # HMC-side time of the newest sample already collected per subsystem,
        # used to only submit samples that were not seen before.
        self.last_sample_time: dict[str, time.struct_time | None] = dict.fromkeys(SAMPLE_FIELDS)


class IbmHmcCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'ibm_hmc'

    # 1 when the check can connect to the HMC over SSH, 0 otherwise. Connectivity
    # is reported as a metric rather than a service check, per repository policy
    # for new integrations; monitor it with e.g.
    # `max(last_5m):avg:ibm_hmc.can_connect{*} by {hmc-instance} < 1`.
    CONNECTIVITY_METRIC = 'can_connect'

    # lslparutil needs a fixed numeric locale, otherwise the HMC may print
    # decimal separators that cannot be parsed as floats.
    LSLPARUTIL_ENV = {'LC_ALL': 'en_US', 'LANG': 'en_US', 'LC_NUMERIC': 'en_US'}
    C_ENV = {'LANG': 'C'}

    # HMC sample time format: 02/23/2006 12:00:01
    SAMPLE_TIME_FORMAT = '%m/%d/%Y %H:%M:%S'

    GET_VERSION_CMD = 'lshmc -v'
    GET_SERVERS_CMD = 'lssyscfg -r sys -F name,type_model,serial_num'
    GET_SAMPLE_RATE_CMD = 'lslparutil -r config -m {name} -F sample_rate'
    GET_TIME_CMD = "date '+%m/%d/%Y %H:%M:%S'"
    SAMPLES_CMD_TEMPLATE = (
        'lslparutil -r {resource} --startyear {year} --startmonth {month} --startday {day} '
        '--starthour {hour} --startminute {minute} -m {name} -F time,{fields} '
        '--filter "event_types=sample"'
    )
    MEMINFO_CMD = 'cat /proc/meminfo'
    SWAP_CMD = 'monhmc -r swap -n 0'

    # Fallback HMC version when `lshmc -v` output cannot be parsed, matching the
    # oldest HMC level whose fields the check knows about.
    DEFAULT_HMC_VERSION = (7, 0, 0)
    # Managed systems are re-discovered at most once per hour.
    SERVER_REFRESH_PERIOD = 3600.0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        # State is keyed per (host, port) so multiple instances never share it.
        self._hmc_versions: dict[tuple[str, int], tuple[int, int, int]] = {}
        self._managed_servers: dict[tuple[str, int], dict[str, ManagedServer]] = {}
        self._last_refresh: dict[tuple[str, int], float] = {}

    def check(self, instance):
        host = self.config.host
        port = self.config.port or 22
        key = (host, port)
        tags = list(self.config.tags or [])
        tags.append(f'hmc-instance:{host}-{port}')

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.load_system_host_keys()

        try:
            try:
                client.connect(host, port=port, username=self.config.username, **self._connect_kwargs())
                self.gauge(self.CONNECTIVITY_METRIC, 1, tags=tags)
            except Exception:
                self.gauge(self.CONNECTIVITY_METRIC, 0, tags=tags)
                raise

            self.collect_metrics(client, key, tags)
        finally:
            # Always close the client, failure to do so leaks one thread per connection left open.
            client.close()

    def collect_metrics(self, client, key, tags):
        if key not in self._hmc_versions:
            self._hmc_versions[key] = self.get_hmc_version(client)
        version = self._hmc_versions[key]

        now = time.time()
        if now - self._last_refresh.get(key, 0) > self.SERVER_REFRESH_PERIOD:
            try:
                self.refresh_managed_servers(client, key)
            except Exception:
                # Keep the current inventory and retry on the next run: a failed
                # discovery must not suppress managed-system metrics for an hour.
                self.log.exception('Unable to refresh the managed servers of %s:%s', *key)
            else:
                self._last_refresh[key] = now

        for server in list(self._managed_servers.get(key, {}).values()):
            if server.sample_rate is None:
                server.sample_rate = self.get_sample_rate(client, server)
                if server.sample_rate is None:
                    continue
            server_tags = [*tags, f'server:{server.name}']
            for subsys in SAMPLE_FIELDS:
                try:
                    self.collect_subsystem(client, subsys, server, version, tags=server_tags)
                except Exception:
                    self.log.exception('Unable to collect %s metrics for %s', subsys, server.name)

        self.collect_meminfo(client, tags)
        self.collect_swap(client, tags)

    def refresh_managed_servers(self, client, key):
        servers = self.get_managed_servers(client)
        managed = self._managed_servers.setdefault(key, {})
        for server in servers:
            managed.setdefault(server.name, server)
        # Drop systems that are no longer managed by this HMC.
        for name in list(managed):
            if name not in {server.name for server in servers}:
                del managed[name]

    def get_hmc_version(self, client):
        """Return the HMC version as a (major, minor, patch) tuple, e.g. `V8R8.4.0.0` is (8, 8, 4).

        `lshmc -v` prints machine-readable lines such as::

            *DS Hardware Management Console
            *RM V8R8.4.0.0

        where the *RM line holds the version, formatted as `V<major>R<minor>.<patch>...`.
        HMC 10 releases have a two-digit major version (e.g. `V10R3.1060.0`), so the
        components must not be collapsed into a single truncated integer.
        """
        output, _, _ = self._exec_command(client, self.GET_VERSION_CMD, environment=self.LSLPARUTIL_ENV)
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == '*RM':
                match = re.match(r'^V(\d+)R(\d+)(?:\.(\d+))?', parts[1])
                if match:
                    return (int(match.group(1)), int(match.group(2)), int(match.group(3) or 0))
                break

        self.log.debug('Unable to parse HMC version from `lshmc -v` output, assuming %s', self.DEFAULT_HMC_VERSION)
        return self.DEFAULT_HMC_VERSION

    def get_managed_servers(self, client):
        """Return the POWER systems managed by the HMC."""
        output, _, status = self._exec_command(client, self.GET_SERVERS_CMD, environment=self.LSLPARUTIL_ENV)
        if status != 0:
            # An empty successful listing is valid (nothing managed), a failed
            # command must be propagated so the caller keeps its inventory.
            raise RuntimeError(f'`lssyscfg -r sys` failed with exit status {status}')

        servers = []
        for line in output.splitlines():
            fields = line.split(',')
            if len(fields) == 3 and fields[0]:
                servers.append(ManagedServer(fields[0], fields[1], fields[2]))
            else:
                self.log.debug('Skipping malformed managed server line: %r', line)
        return servers

    def get_sample_rate(self, client, server):
        """Return the lslparutil sample rate in seconds, or None if it cannot be read."""
        cmd = self.GET_SAMPLE_RATE_CMD.format(name=server.name)
        output, _, status = self._exec_command(client, cmd, environment=self.LSLPARUTIL_ENV)
        if status != 0:
            self.log.error('Unable to collect sample rate for %s: exit status %d', server.name, status)
            return None
        try:
            return int(output.strip())
        except ValueError:
            self.log.error('Unable to collect sample rate for %s: %r', server.name, output.strip())
            return None

    def get_hmc_time(self, client):
        """Return the HMC's current local time as a struct_time.

        The `lslparutil` start options are expressed in HMC-local time, so the
        first collection window must come from the HMC's clock: the Agent's
        local time may be in a different time zone, which would place the
        window past every sample and prevent collection from ever starting.
        """
        output, _, status = self._exec_command(client, self.GET_TIME_CMD, environment=self.C_ENV)
        if status == 0:
            try:
                return time.strptime(output.strip(), self.SAMPLE_TIME_FORMAT)
            except ValueError:
                self.log.warning('Unable to parse HMC time %r, falling back to the Agent clock', output.strip())
        else:
            self.log.warning('Unable to collect the HMC time, falling back to the Agent clock')
        return time.localtime()

    def collect_subsystem(self, client, subsys, server, version, tags):
        """Collect and submit the newest unseen `lslparutil` sample of every series."""
        last_collection = server.last_collection[subsys]
        if last_collection is not None and time.time() - last_collection < server.sample_rate:
            self.log.debug(
                'Skipping %s sampling for %s, not enough time has passed for new samples',
                subsys,
                server.name,
            )
            return

        fields = self._fields_for(subsys, version)
        # Resume from the HMC-side time of the newest sample already collected,
        # or from the HMC's own clock on the first collection of the subsystem.
        last_seen = server.last_sample_time[subsys]
        start_tm = last_seen if last_seen is not None else self.get_hmc_time(client)

        cmd = self.SAMPLES_CMD_TEMPLATE.format(
            resource=subsys.lower(),
            year=start_tm.tm_year,
            month=start_tm.tm_mon,
            day=start_tm.tm_mday,
            hour=start_tm.tm_hour,
            minute=start_tm.tm_min,
            name=server.name,
            fields=','.join(field for field, _ in fields),
        )
        output, _, status = self._exec_command(client, cmd, environment=self.LSLPARUTIL_ENV)
        if status != 0:
            self.log.warning('Unable to collect %s samples for %s: exit status %d', subsys, server.name, status)
            return

        samples = []
        for line in output.splitlines():
            sample = line.split(',')
            if len(sample) != len(fields) + 1:
                self.log.debug('Skipping malformed %s sample for %s: %r', subsys, server.name, line)
                continue
            try:
                sample_time = time.strptime(sample[0], self.SAMPLE_TIME_FORMAT)
            except ValueError:
                self.log.debug('Skipping %s sample with unparsable time %r for %s', subsys, sample[0], server.name)
                continue
            if last_seen is None or sample_time > last_seen:
                samples.append((sample_time, sample))

        if not samples:
            self.log.debug('No new %s samples were collected for %s', subsys, server.name)
            return

        # `lslparutil` returns one row per series and timestamp (e.g. one row per
        # LPAR, or per shared processor pool): keep the newest sample of every
        # series, not just the single newest row overall.
        by_series = {}
        for sample_time, sample in samples:
            series = tuple(sample[i + 1] for i, (_, is_gauge) in enumerate(fields) if not is_gauge)
            current = by_series.get(series)
            if current is None or sample_time > current[0]:
                by_series[series] = (sample_time, sample)

        server.last_collection[subsys] = time.time()
        server.last_sample_time[subsys] = max(sample_time for sample_time, _ in samples)

        for _, sample in by_series.values():
            # Fields that are not metrics are attached as tags to the sample metrics.
            sample_tags = list(tags)
            for i, (field, is_gauge) in enumerate(fields):
                if not is_gauge:
                    sample_tags.append(f'{field}:{sample[i + 1]}')

            for i, (field, is_gauge) in enumerate(fields):
                if not is_gauge:
                    continue
                try:
                    self.gauge(f'{subsys.lower()}.{field}', float(sample[i + 1]), tags=sample_tags)
                except ValueError:
                    self.log.exception('Unable to submit metric %s for %s', field, server.name)

    def collect_meminfo(self, client, tags):
        """Collect the HMC appliance's own memory statistics from /proc/meminfo."""
        output, _, status = self._exec_command(client, self.MEMINFO_CMD, environment=self.C_ENV)
        if status != 0:
            self.log.warning('Unable to collect /proc/meminfo from the HMC: exit status %d', status)
            return

        for line in output.splitlines():
            # MemTotal:      4128368 kB
            parts = line.split()
            if len(parts) < 2 or not parts[0].endswith(':'):
                continue
            try:
                value = float(parts[1])
            except ValueError:
                self.log.debug('Skipping malformed /proc/meminfo line: %r', line)
                continue
            # Normalize names like `HugePages_Total` or `Active(anon)` to valid metric names.
            name = re.sub(r'[^a-z0-9_]+', '_', parts[0][:-1].lower()).strip('_')
            self.gauge(f'system.memory.{name}', value, tags=tags)

    def collect_swap(self, client, tags):
        """Collect the HMC appliance's swap statistics via `monhmc -r swap`."""
        output, _, status = self._exec_command(client, self.SWAP_CMD, environment=self.C_ENV)
        if status != 0:
            self.log.warning('Unable to collect swap statistics from the HMC: exit status %d', status)
            return

        # Swap: 2040244k total, 266000k used, 1774244k free, 2282460k cached
        stats = ' '.join(output.split()[1:])
        for stat in stats.split(','):
            fields = stat.split()
            if len(fields) != 2:
                continue
            value, name = fields
            digits = re.sub(r'\D', '', value)
            if not digits:
                continue
            self.gauge(f'system.memory.swap.{name}', float(digits), tags=tags)

    def _fields_for(self, subsys, version):
        fields = list(SAMPLE_FIELDS[subsys])
        if subsys == 'LPAR':
            for min_version, extras in LPAR_EXTRA_FIELDS:
                if min_version <= version:
                    fields.extend(extras)
        return fields

    def _connect_kwargs(self):
        private_key = self._load_private_key()
        # If the private key is not valid and a password is passed as well,
        # paramiko attempts to use the password for the key, so only one of the
        # two is given at a time.
        connect_kwargs = (
            {'password': self.config.password}
            if private_key is None
            else {
                'passphrase': self.config.password,
                'pkey': private_key,
            }
        )
        if self.config.force_sha1:
            # Some old HMC firmware only supports SHA1 signatures and does not
            # advertise the limitation, so the client has to be told explicitly.
            connect_kwargs['disabled_algorithms'] = {'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']}
        return connect_kwargs

    def _load_private_key(self):
        key_file = self.config.private_key_file
        if key_file is None:
            return None
        try:
            if (self.config.private_key_type or 'rsa') == 'ecdsa':
                return paramiko.ECDSAKey.from_private_key_file(key_file, password=self.config.password)
            return paramiko.RSAKey.from_private_key_file(key_file, password=self.config.password)
        except IOError:
            self.warning('Unable to find private key file: %s', key_file)
        except paramiko.ssh_exception.PasswordRequiredException:
            self.warning('Private key file is encrypted but no password was given')
        except paramiko.ssh_exception.SSHException:
            self.warning('Private key file is invalid')
        return None

    def _exec_command(self, client, command, environment=None):
        """Run a command on the HMC, returning (stdout, stderr, exit status)."""
        _, stdout, stderr = client.exec_command(command, environment=environment)
        output = stdout.read()
        err = stderr.read()
        if isinstance(output, bytes):
            output = output.decode('utf-8', errors='replace')
        if isinstance(err, bytes):
            err = err.decode('utf-8', errors='replace')
        if not output and err:
            self.log.debug('Command %r produced no output, stderr: %s', command, err.strip())
        return output, err, stdout.channel.recv_exit_status()
