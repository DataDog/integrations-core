# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


class DatabaseConfigurationWarning(object):
    """DatabaseConfigurationWarning formalizes the format of database configuration warning messages."""

    def __init__(self, metadata, message, *args):
        if metadata is None:
            metadata = {}
        if args:
            message = message % args
        self._message = message
        self._metadata = metadata

    def __str__(self):
        return '{msg}\n{key_values}'.format(
            msg=self._message,
            key_values=" ".join('{key}={value}'.format(key=k, value=v) for k, v in sorted(self._metadata.items())),
        )
