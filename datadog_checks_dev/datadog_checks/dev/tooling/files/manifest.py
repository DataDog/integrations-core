# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import uuid

from .utils import File

TEMPLATE_IN = """\
graft datadog_checks
graft tests

include MANIFEST.in
include README.md
include requirements.in
include requirements.txt
include requirements-dev.txt
include manifest.json

global-exclude *.py[cod] __pycache__
"""

TEMPLATE_JSON = """\
{{
  "display_name": "{check_name_cap}",
  "maintainer": "{maintainer}",
  "manifest_version": "1.0.0",
  "name": "{check_name}",
  "metric_prefix": "{check_name}.",
  "metric_to_check": "",
  "creates_events": false,
  "short_description": "",
  "guid": "{guid}",
  "support": "{support_type}",
  "supported_os": [
    "linux",
    "mac_os",
    "windows"
  ],
  "public_title": "Datadog-{check_name_cap} Integration",
  "categories": [
    ""
  ],
  "type": "check",
  "doc_link": "https://docs.datadoghq.com/integrations/{check_name}/",
  "is_public": true,
  "has_logo": true
}}
"""


class ManifestIn(File):
    def __init__(self, config):
        super(ManifestIn, self).__init__(
            os.path.join(config['root'], 'MANIFEST.in'),
            TEMPLATE_IN
        )


class ManifestJson(File):
    def __init__(self, config):
        if config['repo_choice'] == 'core':
            maintainer = 'help@datadoghq.com'
            support_type = 'core'
        else:
            maintainer = ''
            support_type = 'contrib'

        super(ManifestJson, self).__init__(
            os.path.join(config['root'], 'manifest.json'),
            TEMPLATE_JSON.format(
                check_name=config['check_name'],
                check_name_cap=config['check_name_cap'],
                maintainer=maintainer,
                support_type=support_type,
                guid=uuid.uuid4(),
            )
        )
