# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.cli.application import Application
from ddev.utils.platform import Platform

PLATFORM = Platform()
APPLICATION = Application(lambda code: print(f"Applicatione exited with code: {code}"), 1, False, False)
