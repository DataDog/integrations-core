
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 5555


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    'openmetrics_endpoint': f"http://{HOST}:{PORT}/metrics",
    'tags': ['test:tag'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

STANDALONE_TEST_METRICS = {
    # Flower event metrics
    'flower_events_total': 'events.total',
    'flower_events_created': 'events.created',
    
    # Task metrics
    'flower_task_runtime_seconds': 'task.runtime.seconds',
    'flower_task_runtime_seconds_created': 'task.runtime.created',
    'flower_task_prefetch_time_seconds': 'task.prefetch_time.seconds',
    
    # Worker metrics
    'flower_worker_prefetched_tasks': 'worker.prefetched_tasks',
    'flower_worker_online': 'worker.online',
    'flower_worker_number_of_currently_executing_tasks': 'worker.executing_tasks',
}
