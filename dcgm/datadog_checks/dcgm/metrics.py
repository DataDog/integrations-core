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
    'DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL': 'nvlink_bandwidth',
    'DCGM_FI_DEV_PCIE_REPLAY_COUNTER': 'pcie_replay',  # becomes pcie_replay.count
    'DCGM_FI_DEV_POWER_USAGE': 'power_usage',
    'DCGM_FI_DEV_SM_CLOCK': 'sm_clock',
    'DCGM_FI_DEV_TOTAL_ENERGY_CONSUMPTION': 'total_energy_consumption',
    'DCGM_FI_DEV_VGPU_LICENSE_STATUS': 'vgpu_license_status',
    'DCGM_FI_DEV_XID_ERRORS': 'xid_errors',
    # Metrics related to memory get grouped together because there are more of them available.
    'DCGM_FI_DEV_MEM_CLOCK': 'mem.clock',
    'DCGM_FI_DEV_MEM_COPY_UTIL': 'mem.copy_utilization',
    'DCGM_FI_DEV_MEMORY_TEMP': 'mem.temperature',
    # NVML Specific Missing Metrics (5)
    'DCGM_FI_DEV_COUNT': 'device',  # becomes device.count
    'DCGM_FI_DEV_FAN_SPEED': 'fan_speed',
    'DCGM_FI_PROF_PCIE_RX_BYTES': 'pcie_rx_throughput',
    'DCGM_FI_PROF_PCIE_TX_BYTES': 'pcie_tx_throughput',
    # Others from default-counters.csv
    'DCGM_FI_DEV_CORRECTABLE_REMAPPED_ROWS': 'correctable_remapped_rows',
    'DCGM_FI_DEV_ROW_REMAP_FAILURE': 'row_remap_failure',
    'DCGM_FI_DEV_UNCORRECTABLE_REMAPPED_ROWS': 'uncorrectable_remapped_rows',
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
