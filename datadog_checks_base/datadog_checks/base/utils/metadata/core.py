# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from six import iteritems

from ..common import to_native_string
from .utils import is_primitive
from .version import parse_version

try:
    import datadog_agent
except ImportError:
    from ...stubs import datadog_agent

LOGGER = logging.getLogger(__file__)


class MetadataManager(object):
    """
    Custom transformers may be defined via a class level attribute `METADATA_TRANSFORMERS`.

    This is a mapping of metadata names to functions. When you call
    `#!python self.set_metadata(name, value, **options)`, if `name` is in this mapping then
    the corresponding function will be called with the `value`, and the return
    value(s) will be collected instead.

    Transformer functions must satisfy the following signature:

    ```python
    def transform_<NAME>(value: Any, options: dict) -> Union[str, Dict[str, str]]:
    ```

    If the return type is `str`, then it will be sent as the value for `name`. If the return type is a mapping type,
    then each key will be considered a `name` and will be sent with its (`str`) value.

    For example, the following would collect an entity named `square` with a value of `'25'`:

    ```python
    from datadog_checks.base import AgentCheck


    class AwesomeCheck(AgentCheck):
        METADATA_TRANSFORMERS = {
            'square': lambda value, options: str(int(value) ** 2)
        }

        def check(self, instance):
            self.set_metadata('square', '5')
    ```

    There are a few default transformers, which can be overridden by custom transformers.
    """

    __slots__ = ('check_id', 'check_name', 'logger', 'metadata_transformers')

    def __init__(self, check_name, check_id, logger=None, metadata_transformers=None):
        self.check_name = check_name
        self.check_id = check_id
        self.logger = logger or LOGGER
        self.metadata_transformers = {'version': self.transform_version}

        if metadata_transformers:
            self.metadata_transformers.update(metadata_transformers)

    def submit_raw(self, name, value):
        datadog_agent.set_check_metadata(self.check_id, to_native_string(name), to_native_string(value))

    def submit(self, name, value, options):
        transformer = self.metadata_transformers.get(name)
        if transformer:
            try:
                transformed = transformer(value, options)
            except Exception as e:
                if is_primitive(value):
                    self.logger.debug('Unable to transform `%s` metadata value `%s`: %s', name, value, e)
                else:
                    self.logger.debug('Unable to transform `%s` metadata: %s', name, e)

                return

            if isinstance(transformed, str):
                self.submit_raw(name, transformed)
            else:
                for transformed_name, transformed_value in iteritems(transformed):
                    self.submit_raw(transformed_name, transformed_value)
        else:
            self.submit_raw(name, value)

    def transform_version(self, version, options):
        """
        Transforms a version like `1.2.3-rc.4+5` to its constituent parts. In all cases,
        the metadata names `version.raw` and `version.scheme` will be collected.

        If a `scheme` is defined then it will be looked up from our known schemes. If no
        scheme is defined then it will default to `semver`. The supported schemes are:

        - `regex` - A `pattern` must also be defined. The pattern must be a `str` or a pre-compiled
          `re.Pattern`. Any matching named subgroups will then be sent as `version.<GROUP_NAME>`. In this case,
          the check name will be used as the value of `version.scheme` unless `final_scheme` is also set, which
          will take precedence.
        - `parts` - A `part_map` must also be defined. Each key in this mapping will be considered
          a `name` and will be sent with its (`str`) value.
        - `semver` - This is essentially the same as `regex` with the `pattern` set to the standard regular
          expression for semantic versioning.

        Taking the example above, calling `#!python self.set_metadata('version', '1.2.3-rc.4+5')` would produce:

        | name | value |
        | --- | --- |
        | `version.raw` | `1.2.3-rc.4+5` |
        | `version.scheme` | `semver` |
        | `version.major` | `1` |
        | `version.minor` | `2` |
        | `version.patch` | `3` |
        | `version.release` | `rc.4` |
        | `version.build` | `5` |
        """
        scheme, version_parts = parse_version(version, options)
        if scheme == 'regex' or scheme == 'parts':
            scheme = options.get('final_scheme', self.check_name)

        data = {'version.{}'.format(part_name): part_value for part_name, part_value in iteritems(version_parts)}
        data['version.raw'] = version
        data['version.scheme'] = scheme

        return data
