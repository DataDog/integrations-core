# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import logging
import re
import subprocess

import requests

log = logging.getLogger('test_downloader')


def test_downloader():
    r = requests.get('https://dd-integrations-core-wheels-build-stable.datadoghq.com/targets/simple/index.html')
    r.raise_for_status()

    for line in r.text.split('\n'):
        pattern = "<a href='(datadog-\\w+?)/'>\\w+?</a><br />"
        match = re.match(pattern, line)

        if match:
            href = match.group(1)
            # -v:     CRITICAL
            # -vv:    ERROR
            # -vvv:   WARNING
            # -vvvv:  INFO
            # -vvvvv: DEBUG
            cmd = ['datadog-checks-downloader', '-vvvv', href]
            out = subprocess.check_output(cmd)
            log.debug(' '.join(cmd))
            log.debug(out)
            log.debug('')
