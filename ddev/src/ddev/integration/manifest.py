# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.utils.json import JSONPointerFile


class Manifest(JSONPointerFile):
    """
    Represents a `manifest.json` file.
    """
