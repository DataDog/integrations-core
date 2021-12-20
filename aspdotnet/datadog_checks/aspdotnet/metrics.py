# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
METRICS_CONFIG = {
    'ASP.NET': {
        'name': 'core',
        'counters': [
            {
                'Application Restarts': {'metric_name': 'application_restarts'},
                'Worker Process Restarts': {'metric_name': 'worker_process_restarts'},
                'Request Wait Time': {'metric_name': 'request.wait_time'},
            }
        ],
    },
    'ASP.NET Applications': {
        'name': 'applications',
        'counters': [
            {
                'Requests In Application Queue': {'metric_name': 'applications.requests.in_queue'},
                'Requests Executing': {'metric_name': 'applications.requests.executing'},
                'Requests/Sec': {'metric_name': 'applications.requests.persec'},
                'Forms Authentication Failure': {'metric_name': 'applications.forms_authentication.failure'},
                'Forms Authentication Success': {'metric_name': 'applications.forms_authentication.successes'},
            }
        ],
    },
}

DEFAULT_COUNTERS = [
    # counterset, instance of counter, counter name, metric name
    # This set is from the Microsoft recommended counters to monitor exchange:
    # https://technet.microsoft.com/en-us/library/dn904093%28v=exchg.150%29.aspx?f=255&MSPPError=-2147217396
    # ASP.Net
    ["ASP.NET", None, "Application Restarts", "aspdotnet.application_restarts", "gauge"],
    ["ASP.NET", None, "Worker Process Restarts", "aspdotnet.worker_process_restarts", "gauge"],
    ["ASP.NET", None, "Request Wait Time", "aspdotnet.request.wait_time", "gauge"],
    # ASP.Net Applications
    [
        "ASP.NET Applications",
        None,
        "Requests In Application Queue",
        "aspdotnet.applications.requests.in_queue",
        "gauge",
    ],
    ["ASP.NET Applications", None, "Requests Executing", "aspdotnet.applications.requests.executing", "gauge"],
    ["ASP.NET Applications", None, "Requests/Sec", "aspdotnet.applications.requests.persec", "gauge"],
    [
        "ASP.NET Applications",
        None,
        "Forms Authentication Failure",
        "aspdotnet.applications.forms_authentication.failure",
        "gauge",
    ],
    [
        "ASP.NET Applications",
        None,
        "Forms Authentication Success",
        "aspdotnet.applications.forms_authentication.successes",
        "gauge",
    ],
]
