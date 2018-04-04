# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Invoke entrypoint, import here all the tasks we want to make available
"""
from __future__ import print_function, unicode_literals

from invoke import Collection

from .cleanup import cleanup
from .manifest import manifest
from .upgrade import upgrade
from .test import test

# the root namespace
root = Collection()

# add tasks to the root, without a namespace
root.add_task(cleanup)
root.add_task(manifest)
root.add_task(upgrade)
root.add_task(test)
