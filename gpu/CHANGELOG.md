# CHANGELOG - GPU

## 0.5.0

***Added***:

* Added Xid errors count metric: `gpu.errors.xid.total`.

## 0.4.1

***Added***:

* Added GPU device level memory metrics: `gpu.memory.free`, `gpu.memory.reserved`.
* Renamed gpu.core.usage to gpu.process.core.usage for naming consistency.
* Renamed gpu.memory.usage to gpu.process.memory.usage for naming consistency.

## 0.4.0

***Added***:

* Added BAR1 GPU memory metrics: `gpu.memory.bar1.free`, `gpu.memory.bar1.total`, `gpu.memory.bar1.used`.

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
