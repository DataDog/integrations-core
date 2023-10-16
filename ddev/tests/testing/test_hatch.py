# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.testing.hatch import get_hatch_env_vars


class TestGetHatchEnvVars:
    def test_no_verbosity(self):
        assert not get_hatch_env_vars(verbosity=0)

    def test_increased_verbosity(self):
        assert get_hatch_env_vars(verbosity=1) == {'HATCH_VERBOSE': '1'}

    def test_decreased_verbosity(self):
        assert get_hatch_env_vars(verbosity=-1) == {'HATCH_QUIET': '1'}
