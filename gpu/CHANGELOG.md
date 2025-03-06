# CHANGELOG - GPU


## 0.2.0

***Added***:

* Added `gpu.core.usage`, `gpu.core.limit`, `gpu.memory.limit` metrics

***Removed***:

* Removed `gpu.utilization` metric as it would yield inaccurate results on certain aggregations. The proper way to compute GPU utilization is to divide `gpu.core.usage` by the `gpu.core.limit`.

## 0.1.0

***Added***:

* Initial release.
