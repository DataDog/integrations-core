# CHANGELOG - GPU


## 0.3.0

***Added***:

* Added process-level GPU metrics with PID tags: `gpu.process.sm_active`, `gpu.process.dram_active`, `gpu.process.encoder_utilization`, and `gpu.process.decoder_utilization`.

## 0.2.0

***Removed***:

* Removed `gpu.utilization` metric as it would yield inaccurate results on certain aggregations. The proper way to compute GPU utilization is to divide `gpu.core.usage` by the `gpu.core.limit`.

***Added***:

* Added `gpu.core.usage`, `gpu.core.limit`, and `gpu.memory.limit` metrics.

## 0.1.0

***Added***:

* Initial release.
