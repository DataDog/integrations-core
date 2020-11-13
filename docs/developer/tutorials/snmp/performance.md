# Performance and Scale

## If collection interval is high

- increase `min_collection_interval` e.g. 300s (the default is 15s)
- increase the number of check runners e.g. 8 or 16 (the default is 4)
- increase `oid_batch_size` e.g. 128 (the default is 10)
