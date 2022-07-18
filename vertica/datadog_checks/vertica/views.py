# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# System tables:
# https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AdministratorsGuide/Monitoring/Vertica/UsingSystemTables.htm
# https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/VerticaSystemTables.htm


class Version:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AdministratorsGuide/Diagnostics/DeterminingYourVersionOfVertica.htm
    """

    name = 'version'
    query = 'SELECT version()'
