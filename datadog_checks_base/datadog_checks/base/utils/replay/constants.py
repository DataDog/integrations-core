# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# TODO: When we drop Python 2 inspect the return type of methods on our stub.
# Until then, assume methods are getters by default since there are few setters.
KNOWN_DATADOG_AGENT_SETTER_METHODS = frozenset({'set_check_metadata', 'write_persistent_cache', 'set_external_tags'})


class EnvVars(object):
    MESSAGE_INDICATOR = 'DD_REPLAY_MESSAGE_INDICATOR'
    CHECK_NAME = 'DD_REPLAY_CHECK_NAME'
    CHECK_ID = 'DD_REPLAY_CHECK_ID'
    INIT_CONFIG = 'DD_REPLAY_INIT_CONFIG'
    INSTANCE = 'DD_REPLAY_INSTANCE'
    DDTRACE = 'DD_TRACE_ENABLED'
