# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
#
# Ported from datadog-unix-agent to integrations-core (Python 3, datadog_checks_base).
# Original: https://github.com/DataDog/datadog-unix-agent/tree/master/checks/bundled/lparstats

import os
import subprocess

from datadog_checks.base import AgentCheck


def _run_cmd(cmd: list[str], sudo: bool = False, timeout: float | None = None) -> tuple[str, str, int]:
    """Run a command, optionally via sudo. Returns (stdout, stderr, returncode)."""
    if sudo:
        cmd = ['sudo'] + list(cmd)
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return (
            result.stdout.decode('utf-8', errors='replace'),
            result.stderr.decode('utf-8', errors='replace'),
            result.returncode,
        )
    except subprocess.TimeoutExpired:
        return '', 'timeout', -1
    except Exception as e:
        return '', str(e), -1


class LPARStats(AgentCheck):
    MEMORY_METRICS_START_IDX = 1
    HYPERVISOR_METRICS_START_IDX = 4
    HYPERVISOR_IDX_METRIC_MAP = {
        0: 'system.lpar.hypervisor.n_calls',
        1: 'system.lpar.hypervisor.time.spent.total',
        2: 'system.lpar.hypervisor.time.spent.hyp',
        3: 'system.lpar.hypervisor.time.call.avg',
        4: 'system.lpar.hypervisor.time.call.max',
    }
    MEMORY_ENTITLEMENTS_START_IDX = 4
    SPURR_PROCESSOR_UTILIZATION_START_IDX = 3
    DEFAULT_TIMEOUT = 5

    def check(self, instance: dict) -> None:
        sudo = instance.get('sudo', False)
        root = (os.getuid() == 0) or sudo
        if not root:
            self.log.info('Not running as root or sudo - entitlement and hypervisor metrics might be unavailable')

        timeout = self.DEFAULT_TIMEOUT

        if instance.get('memory_stats', True):
            self.collect_memory(instance.get('page_stats', True), sudo, timeout)
        if instance.get('memory_entitlements', True) and root:
            self.collect_memory_entitlements(sudo, timeout)
        if instance.get('hypervisor', True) and root:
            self.collect_hypervisor(sudo, timeout)
        if instance.get('spurr_utilization', True):
            self.collect_spurr(sudo, timeout)

    def collect_memory(self, page_stats: bool = True, sudo: bool = False, timeout: float | None = None) -> None:
        cmd = ['lparstat', '-m']
        if page_stats:
            cmd.append('-pw')
        cmd.extend(['1', '1'])

        output, _, _ = _run_cmd(cmd, sudo=sudo, timeout=timeout)
        stats = [line for line in output.splitlines() if line][self.MEMORY_METRICS_START_IDX :]
        if len(stats) < 3:
            self.log.warning('lparstat -m output too short, skipping memory metrics')
            return
        fields = stats[0].split()
        values = stats[2].split()
        for idx, field in enumerate(fields):
            if idx >= len(values):
                break
            try:
                m = float(values[idx])
                if '%' in field:
                    field = field.replace('%', '')
                self.gauge(f'system.lpar.memory.{field}', m)
            except ValueError:
                self.log.info("unable to convert %s to float - skipping", field)

    def collect_hypervisor(self, sudo: bool = False, timeout: float | None = None) -> None:
        cmd = ['lparstat', '-H', '1', '1']
        output, _, _ = _run_cmd(cmd, sudo=sudo, timeout=timeout)
        stats = [line for line in output.splitlines() if line][self.HYPERVISOR_METRICS_START_IDX :]
        if len(stats) < 1:
            self.log.warning('lparstat -H output too short, skipping hypervisor metrics')
            return
        for stat in stats:
            values = stat.split()
            if len(values) < 2:
                continue
            call_tag = f"call:{values[0]}"
            for idx, entry in enumerate(values[1:]):
                if idx not in self.HYPERVISOR_IDX_METRIC_MAP:
                    break
                try:
                    metric_name = self.HYPERVISOR_IDX_METRIC_MAP[idx]
                    metric_value = float(entry)
                    self.gauge(metric_name, metric_value, tags=[call_tag])
                except ValueError:
                    self.log.info(
                        "unable to convert %s to float for %s - skipping",
                        self.HYPERVISOR_IDX_METRIC_MAP.get(idx, idx),
                        call_tag,
                    )

    def collect_memory_entitlements(self, sudo: bool = False, timeout: float | None = None) -> None:
        cmd = ['lparstat', '-m', '-eR', '1', '1']
        output, _, _ = _run_cmd(cmd, sudo=sudo, timeout=timeout)
        stats = [line for line in output.splitlines() if line][self.MEMORY_ENTITLEMENTS_START_IDX :]
        if len(stats) < 2:
            self.log.warning('lparstat -m -eR output too short, skipping entitlement metrics')
            return
        fields = stats[0].split()[1:]
        for stat in stats[1:]:
            values = stat.split()
            if len(values) < 2:
                continue
            tag = f"iompn:{values[0]}"
            for idx, field in enumerate(fields):
                if idx + 1 >= len(values):
                    break
                try:
                    field = field.replace('%', '')
                    metric_name = f"system.lpar.memory.entitlement.{field}"
                    metric_value = float(values[idx + 1])
                    self.gauge(metric_name, metric_value, tags=[tag])
                except ValueError:
                    self.log.info("unable to convert %s to float for %s - skipping", field, tag)

    def collect_spurr(self, sudo: bool = False, timeout: float | None = None) -> None:
        cmd = ['lparstat', '-E', '1', '1']
        output, _, _ = _run_cmd(cmd, sudo=sudo, timeout=timeout)
        table = [line for line in output.splitlines() if line][self.SPURR_PROCESSOR_UTILIZATION_START_IDX :]
        if len(table) < 3:
            self.log.warning('lparstat -E output too short, skipping SPURR metrics')
            return
        fields = table[0].split()
        stats = table[2].split()
        metrics = {}
        total = 0
        total_norm = 0
        metric_tpl = "system.lpar.spurr.{}"
        for idx, field in enumerate(fields):
            if idx >= len(stats):
                break
            metric = metric_tpl.format(field)
            if idx > len(fields) / 2:
                metric = f"{metric}.norm"
            try:
                metrics[metric] = float(stats[idx])
            except ValueError:
                # freq field (e.g. "3.5GHz[100%]") is expected to fail
                self.log.debug("unable to convert %s (%s) to float - skipping", field, stats[idx])
                continue
            if 'norm' in metric:
                total_norm += metrics[metric]
            else:
                total += metrics[metric]

        for metric, val in metrics.items():
            self.gauge(metric, val)
            if 'norm' in metric:
                denom = total_norm
            else:
                denom = total
            if denom > 0:
                self.gauge(f"{metric}.pct", val / denom)
