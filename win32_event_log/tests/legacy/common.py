# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

INSTANCE = {
    'host': ".",
    'tags': ["mytag1", "mytag2"],
    'sites': ["Default Web Site", "Failing site"],
    'logfile': ["Application"],
    'type': ["Error", "Warning"],
    'source_name': ["MSSQLSERVER"],
}


TEST_EVENT = {
    'EventCode': 1000.0,
    'EventIdentifier': 10.0,
    'EventType': 20,
    'InsertionStrings': '[insertionstring]',
    'Logfile': 'Application',
    'Message': 'SomeMessage',
    'SourceName': 'MSQLSERVER',
    'TimeGenerated': '21001224113047.000000-480',
    'User': 'FooUser',
    'Type': 'Error',
}
