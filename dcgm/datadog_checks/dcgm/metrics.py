# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRIC_MAP = {
    # Exposed OM Metrics to map:
    'DCGM_FI_DEV_DEC_UTIL': 'dec_utilization',
    'DCGM_FI_DEV_ENC_UTIL': 'enc_utilization',
    'DCGM_FI_DEV_FB_FREE': 'frame_buffer.free',
    'DCGM_FI_DEV_FB_USED': 'frame_buffer.used',
    'DCGM_FI_DEV_GPU_TEMP': 'temperature',
    'DCGM_FI_DEV_GPU_UTIL': 'gpu_utilization',
    'DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL': {
        'name': 'nvlink_bandwidth',
        'type': 'counter_gauge',
    },  # becomes nvlink_bandwidth.total and nvlink_bandwidth.count
    'DCGM_FI_DEV_PCIE_REPLAY_COUNTER': {
        'name': 'pcie_replay',
        'type': 'counter_gauge',
    },  # becomes pcie_replay.total and pcie_replay.count
    'DCGM_FI_DEV_POWER_USAGE': 'power_usage',
    'DCGM_FI_DEV_SM_CLOCK': 'sm_clock',
    'DCGM_FI_DEV_TOTAL_ENERGY_CONSUMPTION': {
        'name': 'total_energy_consumption',
        'type': 'counter_gauge',
    },  # becomes total_energy_consumption.total and total_energy_consumption.count
    'DCGM_FI_DEV_VGPU_LICENSE_STATUS': 'vgpu_license_status',
    'DCGM_FI_DEV_XID_ERRORS': 'xid_errors',
    # Metrics related to memory get grouped together because there are more of them available.
    'DCGM_FI_DEV_MEM_CLOCK': 'mem.clock',
    'DCGM_FI_DEV_MEM_COPY_UTIL': 'mem.copy_utilization',
    'DCGM_FI_DEV_MEMORY_TEMP': 'mem.temperature',
    # NVML Specific Missing Metrics (5)
    'DCGM_FI_DEV_COUNT': {
        'name': 'device',
        'type': 'counter_gauge',
    },  # becomes device.total and device.count
    'DCGM_FI_DEV_FAN_SPEED': 'fan_speed',
    'DCGM_FI_PROF_PCIE_RX_BYTES': {
        'name': 'pcie_rx_throughput',
        'type': 'counter_gauge',
    },
    'DCGM_FI_PROF_PCIE_TX_BYTES': {
        'name': 'pcie_tx_throughput',
        'type': 'counter_gauge',
    },  # becomes pcie_tx_throughput.total and pcie_tx_throughput.count
    # Others from default-counters.csv
    'DCGM_FI_DEV_CORRECTABLE_REMAPPED_ROWS': 'correctable_remapped_rows',
    'DCGM_FI_DEV_ROW_REMAP_FAILURE': 'row_remap_failure',
    'DCGM_FI_DEV_UNCORRECTABLE_REMAPPED_ROWS': {
        'name': 'uncorrectable_remapped_rows',
        'type': 'counter_gauge',
    },  # becomes uncorrectable_remapped_rows.total and uncorrectable_remapped_rows.count
    # More recommended metrics
    'DCGM_FI_DEV_CLOCK_THROTTLE_REASONS': 'clock_throttle_reasons',
    'DCGM_FI_DEV_FB_RESERVED': 'frame_buffer.reserved',
    'DCGM_FI_DEV_FB_TOTAL': 'frame_buffer.total',
    'DCGM_FI_DEV_FB_USED_PERCENT': 'frame_buffer.used_percent',
    'DCGM_FI_DEV_POWER_MGMT_LIMIT': 'power_management_limit',
    'DCGM_FI_DEV_PSTATE': 'pstate',
    'DCGM_FI_DEV_SLOWDOWN_TEMP': 'slowdown_temperature',
    'DCGM_FI_PROF_DRAM_ACTIVE': 'dram.active',
    'DCGM_FI_PROF_GR_ENGINE_ACTIVE': 'gr_engine_active',
    'DCGM_FI_PROF_PIPE_FP16_ACTIVE': 'pipe.fp16_active',
    'DCGM_FI_PROF_PIPE_FP32_ACTIVE': 'pipe.fp32_active',
    'DCGM_FI_PROF_PIPE_FP64_ACTIVE': 'pipe.fp64_active',
    'DCGM_FI_PROF_PIPE_TENSOR_ACTIVE': 'pipe.tensor_active',
    'DCGM_FI_PROF_SM_ACTIVE': 'sm_active',
    'DCGM_FI_PROF_SM_OCCUPANCY': 'sm_occupancy',
}

RENAME_LABELS_MAP = {
    # Assign the label values as these default tags to make it easier to graph and filter.
    # Since these are exposed from the dcgm exporter, these tags by default point to the exporter
    # instead of the pod that submitted these metrics to the exporter.
    'namespace': 'kube_namespace',
    'pod': 'pod_name',
    'container': 'kube_container_name',
}

IGNORED_TAGS = [
    # Since were using the map to add these tags, we need to disable these from the autodiscovery
    # feature.
    "kube_namespace:.*",
    "pod_name:.*",
    "kube_container_name:.*",
]
