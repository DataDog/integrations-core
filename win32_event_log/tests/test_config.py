# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize('option', ['included_messages', 'excluded_messages'])
def test_invalid_message_filter_regular_expression(dd_run_check, new_check, instance, option):
    instance[option] = ['\\1']
    check = new_check(instance)

    with pytest.raises(
        Exception,
        match='Error compiling pattern for option `{}`: invalid group reference 1 at position 1'.format(option),
    ):
        dd_run_check(check)
