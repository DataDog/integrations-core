# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class OpenStackAuthFailure(Exception):
    pass


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
