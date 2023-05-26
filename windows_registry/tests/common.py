# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# This key is pretty much guaranteed to exist in all environments
INSTANCE = {
    'keypath': 'HKLM\\Software\\Microsoft\\Windows NT\\CurrentVersion',
    'metrics': [
        # This is a REG_SZ
        ['CurrentBuild', 'windows.current_build', 'gauge'],
        # This is a REG_DWORD
        ['InstallDate', 'windows.install_date', 'gauge'],
    ],
}
