# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .utils import File

TEMPLATE_DEV = """\
datadog_checks_dev
"""


class ReqsDevTxt(File):
    def __init__(self, config):
        super(ReqsDevTxt, self).__init__(
            os.path.join(config['root'], 'requirements-dev.txt'),
            TEMPLATE_DEV
        )


class ReqsIn(File):
    def __init__(self, config):
        super(ReqsIn, self).__init__(
            os.path.join(config['root'], 'requirements.in'),
        )


class ReqsTxt(File):
    def __init__(self, config):
        super(ReqsTxt, self).__init__(
            os.path.join(config['root'], 'requirements.txt'),
        )
