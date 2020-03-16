# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import re

from six import iteritems

from ..common import to_native_string
from .constants import DEFAULT_BLACKLIST
from .utils import is_primitive
from .version import parse_version

try:
    import datadog_agent
except ImportError:
    from ...stubs import datadog_agent

LOGGER = logging.getLogger(__file__)


class MetadataManager(object):
    __slots__ = ('check_id', 'check_name', 'logger', 'metadata_transformers')

    def __init__(self, check_name, check_id, logger=None, metadata_transformers=None):
        self.check_name = check_name
        self.check_id = check_id
        self.logger = logger or LOGGER
        self.metadata_transformers = {'config': self.transform_config, 'version': self.transform_version}

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
                    self.logger.warning('Unable to transform `%s` metadata value `%s`: %s', name, value, e)
                else:
                    self.logger.warning('Unable to transform `%s` metadata: %s', name, e)

                return

            if isinstance(transformed, str):
                self.submit_raw(name, transformed)
            else:
                for transformed_name, transformed_value in iteritems(transformed):
                    self.submit_raw(transformed_name, transformed_value)
        else:
            self.submit_raw(name, value)

    def transform_version(self, version, options):
        """Transforms a version like ``1.2.3-rc.4+5`` to its constituent parts. In all cases,
        the metadata names ``version.raw`` and ``version.scheme`` will be sent.

        If a ``scheme`` is defined then it will be looked up from our known schemes. If no
        scheme is defined then it will default to semver.

        The scheme may be set to ``regex`` in which case a ``pattern`` must also be defined. Any matching named
        subgroups will then be sent as ``version.<GROUP_NAME>``. In this case, the check name will be used as
        the value of ``version.scheme`` unless ``final_scheme`` is also set, which will take precedence.
        """
        scheme, version_parts = parse_version(version, options)
        if scheme == 'regex' or scheme == 'parts':
            scheme = options.get('final_scheme', self.check_name)

        data = {'version.{}'.format(part_name): part_value for part_name, part_value in iteritems(version_parts)}
        data['version.raw'] = version
        data['version.scheme'] = scheme

        return data

    def transform_config(self, config, options):
        """This transforms a ``dict`` of arbitrary user configuration. A ``section`` must be defined indicating
        what the configuration represents e.g. ``init_config``.

        The metadata name submitted will become ``config.<section>``.

        The value will be a JSON ``str`` with the root being an array. There will be one map element for every
        allowed field. Every map may have 2 entries:

        1. ``is_set`` - a boolean indicating whether or not the field exists
        2. ``value`` - the value of the field. this is only set if the field exists and the value is a
                       primitive type (``None`` | ``bool`` | ``float`` | ``int`` | ``str``)

        The allowed fields are derived from the optional ``whitelist`` and ``blacklist``. By default, nothing
        will be sent.

        User configuration can override defaults allowing complete, granular control of metadata submissions. In
        any section, one may set ``metadata_whitelist`` and/or ``metadata_blacklist`` which will override their
        keyword argument counterparts. In following our standard, blacklists take precedence over whitelists.

        Blacklists are special in that each item is considered a regular expression.
        """
        section = options.get('section')
        if section is None:
            raise ValueError('The `section` option is required')

        # Although we define the default fields to send in code i.e. the default whitelist, there
        # may be cases where a subclass (for example of OpenMetricsBaseCheck) would want to ignore
        # just a few fields, hence for convenience we have the ability to also pass a blacklist.
        whitelist = config.get('metadata_whitelist', options.get('whitelist')) or ()
        blacklist = config.get('metadata_blacklist', options.get('blacklist', DEFAULT_BLACKLIST)) or ()
        blacklist = re.compile('|'.join(blacklist), re.IGNORECASE)

        transformed_data = {}

        data = []
        for field in whitelist:
            if blacklist.search(field):
                self.logger.debug(
                    'Skipping metadata submission of blacklisted field `%s` in section `%s`', field, section
                )
                continue

            field_data = {}

            if field in config:
                field_data['is_set'] = True

                value = config[field]
                if is_primitive(value):
                    field_data['value'] = value
                else:
                    self.logger.warning(
                        'Skipping metadata submission of non-primitive type `%s` for field `%s` in section `%s`',
                        type(value).__name__,
                        field,
                        section,
                    )
            else:
                field_data['is_set'] = False

            data.append(field_data)

        if data:
            # To avoid the backend having to parse a potentially unbounded number of unique keys, we
            # send `config.<SECTION_NAME>` rather than `config.<SECTION_NAME>.<OPTION_NAME>` since
            # the number of sections is finite (currently only `instance` and `init_config`).
            transformed_data['config.{}'.format(section)] = json.dumps(data)

        return transformed_data
