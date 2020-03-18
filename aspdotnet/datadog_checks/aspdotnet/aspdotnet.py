# (C) Datadog, Inc. 2013-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
try:
    from datadog_checks.base import PDHBaseCheck
except ImportError:

    class PDHBaseCheck:
        pass


EVENT_TYPE = SOURCE_TYPE_NAME = 'aspdotnet'

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


class AspdotnetCheck(PDHBaseCheck):
    def __init__(self, name, init_config, instances=None):
        PDHBaseCheck.__init__(self, name, init_config, instances=instances, counter_list=DEFAULT_COUNTERS)
