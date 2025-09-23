# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRICS_MAP = {
    "kubevirt_virt_controller_leading_status": "virt_controller.leading_status",
    "kubevirt_virt_controller_ready_status": "virt_controller.ready_status",
    "kubevirt_vm_error_status_last_transition_timestamp_seconds": "vm.error_status_last_transition_timestamp_seconds",
    "kubevirt_vm_migrating_status_last_transition_timestamp_seconds": "vm.migrating_status_last_transition_timestamp_seconds",  # noqa: E501
    "kubevirt_vm_non_running_status_last_transition_timestamp_seconds": "vm.non_running_status_last_transition_timestamp_seconds",  # noqa: E501
    "kubevirt_vm_running_status_last_transition_timestamp_seconds": "vm.running_status_last_transition_timestamp_seconds",  # noqa: E501
    "kubevirt_vm_starting_status_last_transition_timestamp_seconds": "vm.starting_status_last_transition_timestamp_seconds",  # noqa: E501
    "kubevirt_vmi_migrations_in_pending_phase": "vmi.migrations_in_pending_phase",
    "kubevirt_vmi_migrations_in_running_phase": "vmi.migrations_in_running_phase",
    "kubevirt_vmi_migrations_in_scheduling_phase": "vmi.migrations_in_scheduling_phase",
    "kubevirt_vmi_non_evictable": "vmi.non_evictable",
    "kubevirt_vmi_number_of_outdated": "vmi.number_of_outdated",
    "kubevirt_vmi_phase_count": "vmi.phase_count",
    "kubevirt_vmi_phase_transition_time_from_creation_seconds": "vmi.phase_transition_time_from_creation_seconds",
    "kubevirt_vmi_phase_transition_time_from_deletion_seconds": "vmi.phase_transition_time_from_deletion_seconds",
    "kubevirt_vmi_phase_transition_time_seconds": "vmi.phase_transition_time_seconds",
    "kubevirt_workqueue_adds": "workqueue.adds",
    "kubevirt_workqueue_depth": "workqueue.depth",
    "kubevirt_workqueue_longest_running_processor_seconds": "workqueue.longest_running_processor_seconds",
    "kubevirt_workqueue_queue_duration_seconds": "workqueue.queue_duration_seconds",
    "kubevirt_workqueue_retries": "workqueue.retries",
    "kubevirt_workqueue_unfinished_work_seconds": "workqueue.unfinished_work_seconds",
    "kubevirt_workqueue_work_duration_seconds": "workqueue.work_duration_seconds",
}
