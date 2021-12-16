# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.aspdotnet.metrics import METRICS_CONFIG

MINIMAL_INSTANCE = {'host': '.'}

INSTANCE_WITH_TAGS = {'host': '.', 'tags': ['tag1', 'another:tag']}

# these metrics are single-instance, so they won't have per-instance tags
ASP_METRICS = ('aspdotnet.application_restarts', 'aspdotnet.worker_process_restarts', 'aspdotnet.request.wait_time')

# these metrics are multi-instance.
ASP_APP_METRICS = (
    # ASP.Net Applications
    'aspdotnet.applications.requests.in_queue',
    'aspdotnet.applications.requests.executing',
    'aspdotnet.applications.requests.persec',
    'aspdotnet.applications.forms_authentication.failure',
    'aspdotnet.applications.forms_authentication.successes',
)

ASP_APP_INSTANCES = (
    '__Total__',
    '_LM_W3SVC_1_ROOT_owa_Calendar',
    '_LM_W3SVC_2_ROOT_Microsoft-Server-ActiveSync',
    '_LM_W3SVC_1_ROOT_Microsoft-Server-ActiveSync',
    '_LM_W3SVC_2_ROOT_ecp',
    '_LM_W3SVC_1_ROOT_ecp',
    '_LM_W3SVC_2_ROOT_Rpc',
    '_LM_W3SVC_1_ROOT_Rpc',
    '_LM_W3SVC_2_ROOT_Autodiscover',
    '_LM_W3SVC_1_ROOT_EWS',
    '_LM_W3SVC_2_ROOT_EWS',
    '_LM_W3SVC_1_ROOT_Autodiscover',
    '_LM_W3SVC_1_ROOT_PowerShell',
    '_LM_W3SVC_2_ROOT_PowerShell',
    '_LM_W3SVC_1_ROOT_OAB',
    '_LM_W3SVC_2_ROOT_owa',
    '_LM_W3SVC_1_ROOT_owa',
)

PERFORMANCE_OBJECTS = {}
for object_name, instances in (('ASP.NET', [None]), ('ASP.NET Applications', ASP_APP_INSTANCES[1:])):
    PERFORMANCE_OBJECTS[object_name] = (
        instances,
        {counter: [9000] * len(instances) for counter in METRICS_CONFIG[object_name]['counters'][0]},
    )
