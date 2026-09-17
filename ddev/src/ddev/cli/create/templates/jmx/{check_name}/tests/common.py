{license_header}
from datadog_checks.dev import get_docker_hostname, get_here, load_jmx_config

HERE = get_here()
HOST = get_docker_hostname()

INSTANCES = [{{'host': 'localhost', 'port': '9999'}}]

CHECK_CONFIG = load_jmx_config()
CHECK_CONFIG['instances'] = INSTANCES
