# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
def get_hatch_env_vars(*, verbosity: int) -> dict[str, str]:
    env_vars = {}

    if verbosity > 0:
        env_vars['HATCH_VERBOSE'] = str(verbosity)
    elif verbosity < 0:
        env_vars['HATCH_QUIET'] = str(abs(verbosity))

    return env_vars
