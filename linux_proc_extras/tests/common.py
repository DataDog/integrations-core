# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

CHECK_NAME = 'linux_proc_extras'

HERE = get_here()
FIXTURE_DIR = os.path.join(HERE, "fixtures")

INSTANCE = {"tags": ["foo:bar"], "include_interrupt_metrics": True}
INSTANCE_NO_INTERRUPT = {"tags": ["foo:bar"], "include_interrupt_metrics": False}

EXPECTED_TAG = "foo:bar"

EXPECTED_BASE_METRICS = [
    'system.inodes.total',
    'system.inodes.used',
    'system.linux.context_switches',
    'system.linux.processes_created',
    'system.linux.interrupts',
    'system.entropy.available',
    'system.processes.states',
    'system.processes.priorities',
]

EXPECTED_METRICS = EXPECTED_BASE_METRICS + ['system.linux.irq']

CPU_COUNT = 4
INTERRUPTS_IDS = [
    "0",
    "1",
    "4",
    "8",
    "9",
    "12",
    "24",
    "25",
    "26",
    "27",
    "28",
    "29",
    "30",
    "31",
    "32",
    "33",
    "34",
    "35",
    "36",
    "NMI",
    "LOC",
    "SPU",
    "PMI",
    "IWI",
    "RTR",
    "RES",
    "CAL",
    "TLB",
    "TRM",
    "THR",
    "DFR",
    "MCE",
    "MCP",
    "PIN",
    "PIW",
]
