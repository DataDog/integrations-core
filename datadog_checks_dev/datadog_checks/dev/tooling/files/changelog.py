# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .utils import File

TEMPLATE = """\
# CHANGELOG - {check_name_cap}

"""


class Changelog(File):
    def __init__(self, config):
        super(Changelog, self).__init__(
            os.path.join(config['root'], 'CHANGELOG.md'),
            TEMPLATE.format(
                check_name_cap=config['check_name_cap'],
            )
        )
