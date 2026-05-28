# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Mapping from raw Prometheus metric names emitted by Flink's
# flink-metrics-prometheus reporter to the namespaced Datadog metric
# names already documented in metadata.csv.
#
# Flink's Prometheus reporter formats names as:
#   flink_<logical_scope>_<metric_name>
# where '_' is the scope separator and any character not matching
# [a-zA-Z0-9:_] is replaced with '_'.
#
# Keys below are the raw Prometheus names (without per-instance labels).
# Values are the DD metric names with the `flink.` namespace stripped --
# the OpenMetricsBaseCheckV2 base class prepends `flink.` from
# `__NAMESPACE__` on the check class.
#
# This map is intentionally a representative subset for the initial
# revision; the full mapping covering every row in metadata.csv will be
# added in a follow-up commit once the design is agreed.
METRIC_MAP = {
    # JobManager JVM
    'flink_jobmanager_Status_JVM_CPU_Load': 'jobmanager.Status.JVM.CPU.Load',
    'flink_jobmanager_Status_JVM_CPU_Time': 'jobmanager.Status.JVM.CPU.Time',
    'flink_jobmanager_Status_JVM_ClassLoader_ClassesLoaded': 'jobmanager.Status.JVM.ClassLoader.ClassesLoaded',
    'flink_jobmanager_Status_JVM_ClassLoader_ClassesUnloaded': 'jobmanager.Status.JVM.ClassLoader.ClassesUnloaded',
    'flink_jobmanager_Status_JVM_Memory_Direct_Count': 'jobmanager.Status.JVM.Memory.Direct.Count',
    'flink_jobmanager_Status_JVM_Memory_Direct_MemoryUsed': 'jobmanager.Status.JVM.Memory.Direct.MemoryUsed',
    'flink_jobmanager_Status_JVM_Memory_Direct_TotalCapacity': 'jobmanager.Status.JVM.Memory.Direct.TotalCapacity',
    'flink_jobmanager_Status_JVM_Memory_Heap_Committed': 'jobmanager.Status.JVM.Memory.Heap.Committed',
    'flink_jobmanager_Status_JVM_Memory_Heap_Max': 'jobmanager.Status.JVM.Memory.Heap.Max',
    'flink_jobmanager_Status_JVM_Memory_Heap_Used': 'jobmanager.Status.JVM.Memory.Heap.Used',
    'flink_jobmanager_Status_JVM_Memory_Mapped_Count': 'jobmanager.Status.JVM.Memory.Mapped.Count',
    'flink_jobmanager_Status_JVM_Memory_Mapped_MemoryUsed': 'jobmanager.Status.JVM.Memory.Mapped.MemoryUsed',
    'flink_jobmanager_Status_JVM_Memory_Mapped_TotalCapacity': 'jobmanager.Status.JVM.Memory.Mapped.TotalCapacity',
    'flink_jobmanager_Status_JVM_Memory_NonHeap_Committed': 'jobmanager.Status.JVM.Memory.NonHeap.Committed',
    'flink_jobmanager_Status_JVM_Memory_NonHeap_Max': 'jobmanager.Status.JVM.Memory.NonHeap.Max',
    'flink_jobmanager_Status_JVM_Memory_NonHeap_Used': 'jobmanager.Status.JVM.Memory.NonHeap.Used',
    'flink_jobmanager_Status_JVM_Threads_Count': 'jobmanager.Status.JVM.Threads.Count',
    # JobManager cluster + job metrics
    'flink_jobmanager_numRegisteredTaskManagers': 'jobmanager.numRegisteredTaskManagers',
    'flink_jobmanager_numRunningJobs': 'jobmanager.numRunningJobs',
    'flink_jobmanager_taskSlotsTotal': 'jobmanager.taskSlotsTotal',
    'flink_jobmanager_job_downtime': 'jobmanager.job.downtime',
    'flink_jobmanager_job_lastCheckpointDuration': 'jobmanager.job.lastCheckpointDuration',
    'flink_jobmanager_job_lastCheckpointSize': 'jobmanager.job.lastCheckpointSize',
    'flink_jobmanager_job_numberOfCompletedCheckpoints': 'jobmanager.job.numberOfCompletedCheckpoints',
    'flink_jobmanager_job_numberOfFailedCheckpoints': 'jobmanager.job.numberOfFailedCheckpoints',
    'flink_jobmanager_job_numberOfInProgressCheckpoints': 'jobmanager.job.numberOfInProgressCheckpoints',
    'flink_jobmanager_job_numRestarts': 'jobmanager.job.numRestarts',
    'flink_jobmanager_job_restartingTime': 'jobmanager.job.restartingTime',
    'flink_jobmanager_job_totalNumberOfCheckpoints': 'jobmanager.job.totalNumberOfCheckpoints',
    # TaskManager JVM
    'flink_taskmanager_Status_JVM_CPU_Load': 'taskmanager.Status.JVM.CPU.Load',
    'flink_taskmanager_Status_JVM_CPU_Time': 'taskmanager.Status.JVM.CPU.Time',
    'flink_taskmanager_Status_JVM_ClassLoader_ClassesLoaded': 'taskmanager.Status.JVM.ClassLoader.ClassesLoaded',
    'flink_taskmanager_Status_JVM_ClassLoader_ClassesUnloaded': 'taskmanager.Status.JVM.ClassLoader.ClassesUnloaded',
    'flink_taskmanager_Status_JVM_Memory_Direct_Count': 'taskmanager.Status.JVM.Memory.Direct.Count',
    'flink_taskmanager_Status_JVM_Memory_Direct_MemoryUsed': 'taskmanager.Status.JVM.Memory.Direct.MemoryUsed',
    'flink_taskmanager_Status_JVM_Memory_Direct_TotalCapacity': 'taskmanager.Status.JVM.Memory.Direct.TotalCapacity',
    'flink_taskmanager_Status_JVM_Memory_Heap_Committed': 'taskmanager.Status.JVM.Memory.Heap.Committed',
    'flink_taskmanager_Status_JVM_Memory_Heap_Max': 'taskmanager.Status.JVM.Memory.Heap.Max',
    'flink_taskmanager_Status_JVM_Memory_Heap_Used': 'taskmanager.Status.JVM.Memory.Heap.Used',
    'flink_taskmanager_Status_JVM_Memory_NonHeap_Committed': 'taskmanager.Status.JVM.Memory.NonHeap.Committed',
    'flink_taskmanager_Status_JVM_Memory_NonHeap_Max': 'taskmanager.Status.JVM.Memory.NonHeap.Max',
    'flink_taskmanager_Status_JVM_Memory_NonHeap_Used': 'taskmanager.Status.JVM.Memory.NonHeap.Used',
    'flink_taskmanager_Status_JVM_Threads_Count': 'taskmanager.Status.JVM.Threads.Count',
    # Task / operator
    'flink_task_numRecordsIn': 'task.numRecordsIn',
    'flink_task_numRecordsOut': 'task.numRecordsOut',
    'flink_task_numBytesOut': 'task.numBytesOut',
    'flink_task_numLateRecordsDropped': 'task.numLateRecordsDropped',
    'flink_operator_numRecordsIn': 'operator.numRecordsIn',
    'flink_operator_numRecordsOut': 'operator.numRecordsOut',
    'flink_operator_numLateRecordsDropped': 'operator.numLateRecordsDropped',
    'flink_operator_currentInputWatermark': 'operator.currentInputWatermark',
    'flink_operator_currentOutputWatermark': 'operator.currentOutputWatermark',
}
