# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
METRICS_CONFIG = {
    'APP_POOL_WAS': {
        'name': 'app_pool',
        'counters': [
            {
                'Current Application Pool State': 'state',
                'Current Application Pool Uptime': 'uptime',
                'Total Application Pool Recycles': {'name': 'recycle.count', 'type': 'monotonic_count'},
            }
        ],
    },
    'Web Service': {
        'name': 'web_service',
        'counters': [
            {
                'Service Uptime': {'metric_name': 'uptime'},
                # Network
                'Bytes Sent/sec': {'metric_name': 'net.bytes_sent'},
                'Bytes Received/sec': {'metric_name': 'net.bytes_rcvd'},
                'Bytes Total/sec': {'metric_name': 'net.bytes_total'},
                'Current Connections': {'metric_name': 'net.num_connections'},
                'Files Sent/sec': {'metric_name': 'net.files_sent'},
                'Files Received/sec': {'metric_name': 'net.files_rcvd'},
                'Total Connection Attempts (all instances)': {'metric_name': 'net.connection_attempts'},
                'Connection Attempts/sec': {'metric_name': 'net.connection_attempts_sec'},
                # HTTP methods
                'Get Requests/sec': {'metric_name': 'httpd_request_method.get'},
                'Post Requests/sec': {'metric_name': 'httpd_request_method.post'},
                'Head Requests/sec': {'metric_name': 'httpd_request_method.head'},
                'Put Requests/sec': {'metric_name': 'httpd_request_method.put'},
                'Delete Requests/sec': {'metric_name': 'httpd_request_method.delete'},
                'Options Requests/sec': {'metric_name': 'httpd_request_method.options'},
                'Trace Requests/sec': {'metric_name': 'httpd_request_method.trace'},
                # Errors
                'Not Found Errors/sec': {'metric_name': 'errors.not_found'},
                'Locked Errors/sec': {'metric_name': 'errors.locked'},
                # Users
                'Anonymous Users/sec': {'metric_name': 'users.anon'},
                'NonAnonymous Users/sec': {'metric_name': 'users.nonanon'},
                # Requests
                'CGI Requests/sec': {'metric_name': 'requests.cgi'},
                'ISAPI Extension Requests/sec': {'metric_name': 'requests.isapi'},
            }
        ],
    },
}
