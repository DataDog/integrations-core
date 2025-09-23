# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.integration.manifest import Manifest
from ddev.utils.json import JSONPointerFile


def test_core_functionality():
    assert issubclass(Manifest, JSONPointerFile)
