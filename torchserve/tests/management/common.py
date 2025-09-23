# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Some tag values can't be predicted, pid for instance
NON_PREDICTABLE_TAGS = (
    "worker_id",
    "worker_pid",
)

METRICS = [
    {
        "name": "torchserve.management_api.models",
        "value": 5,
    },
    # linear_regression_1_1
    {
        "name": "torchserve.management_api.model.versions",
        "value": 1,
        "tags": ['model_name:linear_regression_1_1'],
    },
    {
        "name": "torchserve.management_api.model.workers.current",
        "value": 2,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.workers.min",
        "value": 2,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.workers.max",
        "value": 4,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.batch_size",
        "value": 1,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.max_batch_delay",
        "value": 100,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.is_loaded_at_startup",
        "value": 0,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.version.is_default",
        "value": 1,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.worker.memory_usage",
        "value": 418390016,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1', 'worker_id:9000', 'worker_pid:46'],
    },
    {
        "name": "torchserve.management_api.model.worker.status",
        "value": 2,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1', 'worker_id:9000', 'worker_pid:46'],
    },
    {
        "name": "torchserve.management_api.model.worker.memory_usage",
        "value": 418390017,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1', 'worker_id:9007', 'worker_pid:666'],
    },
    {
        "name": "torchserve.management_api.model.worker.status",
        "value": 3,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1', 'worker_id:9007', 'worker_pid:666'],
    },
    {
        "name": "torchserve.management_api.model.worker.is_gpu",
        "value": 1,
        "tags": ['model_name:linear_regression_1_1', 'model_version:1', 'worker_id:9007', 'worker_pid:666'],
    },
    # linear_regression_1_2
    {
        "name": "torchserve.management_api.model.versions",
        "value": 3,
        "tags": ['model_name:linear_regression_1_2'],
    },
    {
        "name": "torchserve.management_api.model.workers.current",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.workers.min",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.workers.max",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.batch_size",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.max_batch_delay",
        "value": 100,
        "tags": ['model_name:linear_regression_1_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.is_loaded_at_startup",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.version.is_default",
        "value": 0,
        "tags": ['model_name:linear_regression_1_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.worker.memory_usage",
        "value": 417181696,
        "tags": ['model_name:linear_regression_1_2', 'model_version:1', 'worker_id:9001', 'worker_pid:50'],
    },
    {
        "name": "torchserve.management_api.model.worker.status",
        "value": 0,
        "tags": ['model_name:linear_regression_1_2', 'model_version:1', 'worker_id:9001', 'worker_pid:50'],
    },
    {
        "name": "torchserve.management_api.model.worker.is_gpu",
        "value": 0,
        "tags": ['model_name:linear_regression_1_2', 'model_version:1', 'worker_id:9001', 'worker_pid:50'],
    },
    {
        "name": "torchserve.management_api.model.workers.current",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:2'],
    },
    {
        "name": "torchserve.management_api.model.workers.min",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:2'],
    },
    {
        "name": "torchserve.management_api.model.workers.max",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:2'],
    },
    {
        "name": "torchserve.management_api.model.batch_size",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:2'],
    },
    {
        "name": "torchserve.management_api.model.max_batch_delay",
        "value": 100,
        "tags": ['model_name:linear_regression_1_2', 'model_version:2'],
    },
    {
        "name": "torchserve.management_api.model.is_loaded_at_startup",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:2'],
    },
    {
        "name": "torchserve.management_api.model.version.is_default",
        "value": 0,
        "tags": ['model_name:linear_regression_1_2', 'model_version:2'],
    },
    {
        "name": "torchserve.management_api.model.worker.memory_usage",
        "value": 413630464,
        "tags": ['model_name:linear_regression_1_2', 'model_version:2', 'worker_id:9002', 'worker_pid:56'],
    },
    {
        "name": "torchserve.management_api.model.worker.status",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:2', 'worker_id:9002', 'worker_pid:56'],
    },
    {
        "name": "torchserve.management_api.model.worker.is_gpu",
        "value": 0,
        "tags": ['model_name:linear_regression_1_2', 'model_version:2', 'worker_id:9002', 'worker_pid:56'],
    },
    {
        "name": "torchserve.management_api.model.workers.current",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:3'],
    },
    {
        "name": "torchserve.management_api.model.workers.min",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:3'],
    },
    {
        "name": "torchserve.management_api.model.workers.max",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:3'],
    },
    {
        "name": "torchserve.management_api.model.batch_size",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:3'],
    },
    {
        "name": "torchserve.management_api.model.max_batch_delay",
        "value": 100,
        "tags": ['model_name:linear_regression_1_2', 'model_version:3'],
    },
    {
        "name": "torchserve.management_api.model.is_loaded_at_startup",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:3'],
    },
    {
        "name": "torchserve.management_api.model.version.is_default",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:3'],
    },
    {
        "name": "torchserve.management_api.model.worker.memory_usage",
        "value": 416645120,
        "tags": ['model_name:linear_regression_1_2', 'model_version:3', 'worker_id:9003', 'worker_pid:66'],
    },
    {
        "name": "torchserve.management_api.model.worker.status",
        "value": 1,
        "tags": ['model_name:linear_regression_1_2', 'model_version:3', 'worker_id:9003', 'worker_pid:66'],
    },
    {
        "name": "torchserve.management_api.model.worker.is_gpu",
        "value": 0,
        "tags": ['model_name:linear_regression_1_2', 'model_version:3', 'worker_id:9003', 'worker_pid:66'],
    },
    # linear_regression_2_2
    {
        "name": "torchserve.management_api.model.versions",
        "value": 1,
        "tags": ['model_name:linear_regression_2_2'],
    },
    {
        "name": "torchserve.management_api.model.workers.current",
        "value": 1,
        "tags": ['model_name:linear_regression_2_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.workers.min",
        "value": 1,
        "tags": ['model_name:linear_regression_2_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.workers.max",
        "value": 1,
        "tags": ['model_name:linear_regression_2_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.batch_size",
        "value": 1,
        "tags": ['model_name:linear_regression_2_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.max_batch_delay",
        "value": 100,
        "tags": ['model_name:linear_regression_2_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.is_loaded_at_startup",
        "value": 1,
        "tags": ['model_name:linear_regression_2_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.version.is_default",
        "value": 1,
        "tags": ['model_name:linear_regression_2_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.worker.memory_usage",
        "value": 417554432,
        "tags": ['model_name:linear_regression_2_2', 'model_version:1', 'worker_id:9004', 'worker_pid:77'],
    },
    {
        "name": "torchserve.management_api.model.worker.status",
        "value": 1,
        "tags": ['model_name:linear_regression_2_2', 'model_version:1', 'worker_id:9004', 'worker_pid:77'],
    },
    {
        "name": "torchserve.management_api.model.worker.is_gpu",
        "value": 0,
        "tags": ['model_name:linear_regression_2_2', 'model_version:1', 'worker_id:9004', 'worker_pid:77'],
    },
    # linear_regression_2_3
    {
        "name": "torchserve.management_api.model.versions",
        "value": 1,
        "tags": ['model_name:linear_regression_2_3'],
    },
    {
        "name": "torchserve.management_api.model.workers.current",
        "value": 1,
        "tags": ['model_name:linear_regression_2_3', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.workers.min",
        "value": 1,
        "tags": ['model_name:linear_regression_2_3', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.workers.max",
        "value": 1,
        "tags": ['model_name:linear_regression_2_3', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.batch_size",
        "value": 1,
        "tags": ['model_name:linear_regression_2_3', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.max_batch_delay",
        "value": 100,
        "tags": ['model_name:linear_regression_2_3', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.is_loaded_at_startup",
        "value": 1,
        "tags": ['model_name:linear_regression_2_3', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.version.is_default",
        "value": 1,
        "tags": ['model_name:linear_regression_2_3', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.worker.memory_usage",
        "value": 416874496,
        "tags": ['model_name:linear_regression_2_3', 'model_version:1', 'worker_id:9005', 'worker_pid:81'],
    },
    {
        "name": "torchserve.management_api.model.worker.status",
        "value": 1,
        "tags": ['model_name:linear_regression_2_3', 'model_version:1', 'worker_id:9005', 'worker_pid:81'],
    },
    {
        "name": "torchserve.management_api.model.worker.is_gpu",
        "value": 0,
        "tags": ['model_name:linear_regression_2_3', 'model_version:1', 'worker_id:9005', 'worker_pid:81'],
    },
    # linear_regression_3_2
    {
        "name": "torchserve.management_api.model.versions",
        "value": 1,
        "tags": ['model_name:linear_regression_3_2'],
    },
    {
        "name": "torchserve.management_api.model.workers.current",
        "value": 1,
        "tags": ['model_name:linear_regression_3_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.workers.min",
        "value": 1,
        "tags": ['model_name:linear_regression_3_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.workers.max",
        "value": 1,
        "tags": ['model_name:linear_regression_3_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.batch_size",
        "value": 1,
        "tags": ['model_name:linear_regression_3_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.max_batch_delay",
        "value": 100,
        "tags": ['model_name:linear_regression_3_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.is_loaded_at_startup",
        "value": 1,
        "tags": ['model_name:linear_regression_3_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.version.is_default",
        "value": 1,
        "tags": ['model_name:linear_regression_3_2', 'model_version:1'],
    },
    {
        "name": "torchserve.management_api.model.worker.memory_usage",
        "value": 417431552,
        "tags": ['model_name:linear_regression_3_2', 'model_version:1', 'worker_id:9006', 'worker_pid:89'],
    },
    {
        "name": "torchserve.management_api.model.worker.status",
        "value": 1,
        "tags": ['model_name:linear_regression_3_2', 'model_version:1', 'worker_id:9006', 'worker_pid:89'],
    },
    {
        "name": "torchserve.management_api.model.worker.is_gpu",
        "value": 0,
        "tags": ['model_name:linear_regression_3_2', 'model_version:1', 'worker_id:9006', 'worker_pid:89'],
    },
]
