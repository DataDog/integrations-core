# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


class InstancePowerOffFailure(Exception):
    pass


class IncompleteConfig(Exception):
    pass


class IncompleteAuthScope(IncompleteConfig):
    pass


class IncompleteIdentity(IncompleteConfig):
    pass


class MissingEndpoint(Exception):
    pass


class MissingNovaEndpoint(MissingEndpoint):
    pass


class MissingNeutronEndpoint(MissingEndpoint):
    pass


class KeystoneUnreachable(Exception):
    pass


class KeystoneScope(Exception):
    pass
