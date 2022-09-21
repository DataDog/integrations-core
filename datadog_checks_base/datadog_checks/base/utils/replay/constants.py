# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# There are few setters so assume methods are getters by default
KNOWN_DATADOG_AGENT_SETTER_METHODS = frozenset({'set_check_metadata', 'write_persistent_cache', 'set_external_tags'})


class EnvVars(object):
    MESSAGE_INDICATOR = 'DD_REPLAY_MESSAGE_INDICATOR'
    CHECK_NAME = 'DD_REPLAY_CHECK_NAME'
    CHECK_ID = 'DD_REPLAY_CHECK_ID'
    INIT_CONFIG = 'DD_REPLAY_INIT_CONFIG'
    INSTANCE = 'DD_REPLAY_INSTANCE'
