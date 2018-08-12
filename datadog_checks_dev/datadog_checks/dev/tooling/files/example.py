# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .utils import File

TEMPLATE = """\
init_config:

instances:
  - {}
"""


class ExampleConf(File):
    def __init__(self, config):
        super(ExampleConf, self).__init__(
            os.path.join(config['root'], 'datadog_checks', config['check_name'], 'data', 'conf.yaml.example'),
            TEMPLATE
        )
