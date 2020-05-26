# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from pyVmomi import vim

from datadog_checks.vsphere.legacy.event import ALLOWED_EVENTS


def test_allowed_event_list():
    expected_events = [
        vim.event.AlarmStatusChangedEvent,
        vim.event.TaskEvent,
        vim.event.VmBeingHotMigratedEvent,
        vim.event.VmMessageEvent,
        vim.event.VmMigratedEvent,
        vim.event.VmPoweredOnEvent,
        vim.event.VmPoweredOffEvent,
        vim.event.VmReconfiguredEvent,
        vim.event.VmSuspendedEvent,
    ]
    assert sorted(str(e) for e in expected_events) == sorted(str(e) for e in ALLOWED_EVENTS)
