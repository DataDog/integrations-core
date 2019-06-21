# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
CHECK_NAME = 'iis'
MINIMAL_INSTANCE = {'host': '.'}

INSTANCE = {'host': '.', 'sites': ['Default Web Site', 'Exchange Back End', 'Non Existing Website']}

INVALID_HOST_INSTANCE = {'host': 'nonexistinghost'}

WIN_SERVICES_MINIMAL_CONFIG = {'host': ".", 'tags': ["mytag1", "mytag2"]}

WIN_SERVICES_CONFIG = {
    'host': ".",
    'tags': ["mytag1", "mytag2"],
    'sites': ["Default Web Site", "Exchange Back End", "Failing site"],
}
