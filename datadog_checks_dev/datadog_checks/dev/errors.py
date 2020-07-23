# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class RetryError(Exception):
    pass


class SubprocessError(Exception):
    pass


class ManifestError(Exception):
    """
    Raised when the manifest.json file is malformed
    """

    pass
