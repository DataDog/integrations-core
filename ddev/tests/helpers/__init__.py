# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys
from typing import NoReturn

from ddev.cli.application import Application
from ddev.utils.platform import Platform


def _exit(code: int) -> NoReturn:
    print(f"Application exited with code: {code}")
    sys.exit(code)


PLATFORM = Platform()
APPLICATION = Application(_exit, 1, False, False)
LOCAL_REPO_BRANCH = "ddev-testing"
