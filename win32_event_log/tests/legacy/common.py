# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


from datadog_checks.base.checks.win.wmi.sampler import CaseInsensitiveDict

INSTANCE = {
    'host': ".",
    'tags': ["mytag1", "mytag2"],
    'sites': ["Default Web Site", "Failing site"],
    'logfile': ["Application"],
    'type': ["Error", "Warning"],
    'source_name': ["MSSQLSERVER"],
}


TEST_EVENT = CaseInsensitiveDict(
    {
        'eventcode': 1000.0,
        'eventidentifier': 10.0,
        'eventtype': 20,
        'insertionstrings': '[insertionstring]',
        'logfile': 'Application',
        'message': 'SomeMessage',
        'sourcename': 'MSQLSERVER',
        'timegenerated': '21001224113047.000000-480',
        'user': 'FooUser',
        'type': 'Error',
    }
)
