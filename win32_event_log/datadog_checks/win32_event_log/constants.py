# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# See:
# https://docs.microsoft.com/en-us/windows/win32/eventlog/event-types
# https://docs.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-reporteventa#parameters
# https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-even/1ed850f9-a1fe-4567-a371-02683c6ed3cb
#
# However, event viewer & the C api do not show the constants from above, but rather return these:
# https://docs.microsoft.com/en-us/windows/win32/wes/eventmanifestschema-leveltype-complextype#remarks
EVENT_TYPES = {
    'success': 4,
    'error': 2,
    'warning': 3,
    'information': 4,
    'success audit': 4,
    'failure audit': 2,
}
