# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .utils import File

TEMPLATE = """\
metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name
"""


class MetadataCsv(File):
    def __init__(self, config):
        super(MetadataCsv, self).__init__(
            os.path.join(config['root'], 'metadata.csv'),
            TEMPLATE
        )
