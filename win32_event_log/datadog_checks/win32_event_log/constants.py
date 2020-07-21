# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
EVENT_TYPE = 'win32_log_event'
SOURCE_TYPE_NAME = 'event viewer'

# Integer properties to normalize.
# Source: https://docs.microsoft.com/en-us/previous-versions/windows/desktop/eventlogprov/win32-ntlogevent
INTEGER_PROPERTIES = ['EventCode', 'EventIdentifier', 'EventType', 'RecordNumber']
