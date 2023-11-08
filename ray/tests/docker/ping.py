# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Script used for docker healthcheck because curl is not installed (and I want to avoid building a custom image)

import sys
from urllib.request import Request, urlopen

with urlopen(Request(sys.argv[1])) as response:
    if response.status == 200:
        exit(0)
    else:
        exit(1)
