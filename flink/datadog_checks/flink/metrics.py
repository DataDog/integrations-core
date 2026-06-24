# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# flake8: noqa: E501

# Mapping from raw Prometheus metric names emitted by Flink's
# flink-metrics-prometheus reporter to the namespaced Datadog metric
# names already documented in metadata.csv.
#
# Flink's Prometheus reporter formats names as:
#   flink_<logical_scope>_<metric_name>
# where `<logical_scope>` is one of Flink's hardcoded internal scopes
# (`jobmanager`, `jobmanager_job`, `taskmanager`, `taskmanager_job`,
# `taskmanager_job_task`, `taskmanager_job_task_operator`) and is
# *not* affected by the `metrics.scope.*` configuration overrides --
# those only apply to non-Prometheus reporters. Tasks and operators
# therefore land under the long `taskmanager_job_task[_operator]_*`
# prefix on the raw side, even though metadata.csv historically
# documents the DD-side as the shorter `flink.task.*` / `flink.operator.*`.
#
# Keys are the raw Prometheus names; values are the DD metric names
# with the `flink.` namespace stripped -- the OpenMetricsBaseCheckV2
# base class prepends `flink.` from `__NAMESPACE__` on the check class.
METRIC_MAP = {
    # JobManager
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
    'flink_jobmanager_job_downtime': 'jobmanager.job.downtime',
    'flink_jobmanager_job_lastCheckpointAlignmentBuffered': 'jobmanager.job.lastCheckpointAlignmentBuffered',
    'flink_jobmanager_job_lastCheckpointDuration': 'jobmanager.job.lastCheckpointDuration',
    'flink_jobmanager_job_lastCheckpointExternalPath': 'jobmanager.job.lastCheckpointExternalPath',
    'flink_jobmanager_job_lastCheckpointRestoreTimestamp': 'jobmanager.job.lastCheckpointRestoreTimestamp',
    'flink_jobmanager_job_lastCheckpointSize': 'jobmanager.job.lastCheckpointSize',
    'flink_jobmanager_job_numRestarts': 'jobmanager.job.numRestarts',
    'flink_jobmanager_job_numberOfCompletedCheckpoints': 'jobmanager.job.numberOfCompletedCheckpoints',
    'flink_jobmanager_job_numberOfFailedCheckpoints': 'jobmanager.job.numberOfFailedCheckpoints',
    'flink_jobmanager_job_numberOfInProgressCheckpoints': 'jobmanager.job.numberOfInProgressCheckpoints',
    'flink_jobmanager_job_restartingTime': 'jobmanager.job.restartingTime',
    'flink_jobmanager_job_totalNumberOfCheckpoints': 'jobmanager.job.totalNumberOfCheckpoints',
    'flink_jobmanager_job_uptime': 'jobmanager.job.uptime',
    'flink_jobmanager_numRegisteredTaskManagers': 'jobmanager.numRegisteredTaskManagers',
    'flink_jobmanager_numRunningJobs': 'jobmanager.numRunningJobs',
    'flink_jobmanager_taskSlotsTotal': 'jobmanager.taskSlotsTotal',
    # TaskManager
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
    'flink_taskmanager_Status_JVM_Memory_Mapped_Count': 'taskmanager.Status.JVM.Memory.Mapped.Count',
    'flink_taskmanager_Status_JVM_Memory_Mapped_MemoryUsed': 'taskmanager.Status.JVM.Memory.Mapped.MemoryUsed',
    'flink_taskmanager_Status_JVM_Memory_Mapped_TotalCapacity': 'taskmanager.Status.JVM.Memory.Mapped.TotalCapacity',
    'flink_taskmanager_Status_JVM_Memory_NonHeap_Committed': 'taskmanager.Status.JVM.Memory.NonHeap.Committed',
    'flink_taskmanager_Status_JVM_Memory_NonHeap_Max': 'taskmanager.Status.JVM.Memory.NonHeap.Max',
    'flink_taskmanager_Status_JVM_Memory_NonHeap_Used': 'taskmanager.Status.JVM.Memory.NonHeap.Used',
    'flink_taskmanager_Status_JVM_Threads_Count': 'taskmanager.Status.JVM.Threads.Count',
    'flink_taskmanager_Status_Shuffle_Netty_AvailableMemorySegments': 'taskmanager.Status.Shuffle.Netty.AvailableMemorySegments',
    'flink_taskmanager_Status_Shuffle_Netty_TotalMemorySegments': 'taskmanager.Status.Shuffle.Netty.TotalMemorySegments',
    # Task
    'flink_taskmanager_job_task_Shuffle_Netty_Input_Buffers_inPoolUsage': 'task.Shuffle.Netty.Input.Buffers.inPoolUsage',
    'flink_taskmanager_job_task_Shuffle_Netty_Input_Buffers_inputQueueLength': 'task.Shuffle.Netty.Input.Buffers.inputQueueLength',
    'flink_taskmanager_job_task_Shuffle_Netty_Input_numBuffersInLocal': 'task.Shuffle.Netty.Input.numBuffersInLocal',
    'flink_taskmanager_job_task_Shuffle_Netty_Input_numBuffersInLocalPerSecond': 'task.Shuffle.Netty.Input.numBuffersInLocalPerSecond',
    'flink_taskmanager_job_task_Shuffle_Netty_Input_numBuffersInRemote': 'task.Shuffle.Netty.Input.numBuffersInRemote',
    'flink_taskmanager_job_task_Shuffle_Netty_Input_numBuffersInRemotePerSecond': 'task.Shuffle.Netty.Input.numBuffersInRemotePerSecond',
    'flink_taskmanager_job_task_Shuffle_Netty_Input_numBytesInLocal': 'task.Shuffle.Netty.Input.numBytesInLocal',
    'flink_taskmanager_job_task_Shuffle_Netty_Input_numBytesInLocalPerSecond': 'task.Shuffle.Netty.Input.numBytesInLocalPerSecond',
    'flink_taskmanager_job_task_Shuffle_Netty_Input_numBytesInRemote': 'task.Shuffle.Netty.Input.numBytesInRemote',
    'flink_taskmanager_job_task_Shuffle_Netty_Input_numBytesInRemotePerSecond': 'task.Shuffle.Netty.Input.numBytesInRemotePerSecond',
    'flink_taskmanager_job_task_Shuffle_Netty_Output_Buffers_outPoolUsage': 'task.Shuffle.Netty.Output.Buffers.outPoolUsage',
    'flink_taskmanager_job_task_Shuffle_Netty_Output_Buffers_outputQueueLength': 'task.Shuffle.Netty.Output.Buffers.outputQueueLength',
    'flink_taskmanager_job_task_checkpointAlignmentTime': 'task.checkpointAlignmentTime',
    'flink_taskmanager_job_task_currentInputWatermark': 'task.currentInputWatermark',
    'flink_taskmanager_job_task_numBuffersOut': 'task.numBuffersOut',
    'flink_taskmanager_job_task_numBuffersOutPerSecond': 'task.numBuffersOutPerSecond',
    'flink_taskmanager_job_task_numBytesOut': 'task.numBytesOut',
    'flink_taskmanager_job_task_numBytesOutPerSecond': 'task.numBytesOutPerSecond',
    'flink_taskmanager_job_task_numLateRecordsDropped': 'task.numLateRecordsDropped',
    'flink_taskmanager_job_task_numRecordsIn': 'task.numRecordsIn',
    'flink_taskmanager_job_task_numRecordsInPerSecond': 'task.numRecordsInPerSecond',
    'flink_taskmanager_job_task_numRecordsOut': 'task.numRecordsOut',
    # `numRecordsOutPerSec` (truncated suffix) is a pre-existing asymmetry in
    # metadata.csv; the raw Prometheus name uses the full word `PerSecond`.
    'flink_taskmanager_job_task_numRecordsOutPerSecond': 'task.numRecordsOutPerSec',
    # Operator
    'flink_taskmanager_job_task_operator_commitsFailed': 'operator.commitsFailed',
    'flink_taskmanager_job_task_operator_commitsSucceeded': 'operator.commitsSucceeded',
    'flink_taskmanager_job_task_operator_currentInput1Watermark': 'operator.currentInput1Watermark',
    'flink_taskmanager_job_task_operator_currentInput2Watermark': 'operator.currentInput2Watermark',
    'flink_taskmanager_job_task_operator_currentInputWatermark': 'operator.currentInputWatermark',
    'flink_taskmanager_job_task_operator_currentOutputWatermark': 'operator.currentOutputWatermark',
    'flink_taskmanager_job_task_operator_numLateRecordsDropped': 'operator.numLateRecordsDropped',
    'flink_taskmanager_job_task_operator_numRecordsIn': 'operator.numRecordsIn',
    'flink_taskmanager_job_task_operator_numRecordsInPerSecond': 'operator.numRecordsInPerSecond',
    'flink_taskmanager_job_task_operator_numRecordsOut': 'operator.numRecordsOut',
    'flink_taskmanager_job_task_operator_numRecordsOutPerSecond': 'operator.numRecordsOutPerSec',
    'flink_taskmanager_job_task_operator_numSplitsProcessed': 'operator.numSplitsProcessed',
}
