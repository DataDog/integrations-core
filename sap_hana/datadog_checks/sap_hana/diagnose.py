# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from contextlib import closing
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sap_hana import SapHanaCheck

_MINIMUM_MAJOR_VERSION = 2
_CATEGORY = "SAP HANA"

_CATALOG_VIEWS = ['SYS.SCHEMAS', 'SYS.M_TABLES', 'SYS.VIEWS', 'SYS.TABLE_COLUMNS', 'SYS.VIEW_COLUMNS']

DIAGNOSTIC_METADATA = {
    'connection_failure': {
        'description': "Unable to connect to SAP HANA at the configured host and port.",
        'remediation': (
            "Verify that server, port, username, and password are correct and that the HANA instance is reachable."
        ),
    },
    'version_unsupported': {
        'description': "The SAP HANA version is below the minimum supported version ({}.x).".format(
            _MINIMUM_MAJOR_VERSION
        ),
        'remediation': "Upgrade to SAP HANA 2.0 or later.",
    },
    'missing_catalog_privilege': {
        'description': (
            "The configured user lacks SELECT privilege on one or more system catalog views "
            "required for schema collection: {}.".format(', '.join(_CATALOG_VIEWS))
        ),
        'remediation': (
            "Grant SELECT on SYS.SCHEMAS, SYS.M_TABLES, SYS.VIEWS, SYS.TABLE_COLUMNS, and SYS.VIEW_COLUMNS "
            "to the monitoring user, or grant the CATALOG READ system privilege."
        ),
    },
    'catalog_view_inaccessible': {
        'description': "A system catalog view required for schema collection could not be queried.",
        'remediation': "Verify the HANA instance is healthy and the system catalog views are accessible.",
    },
}


class HanaConfigurationError(Enum):
    connection_failure = 'connection_failure'
    version_unsupported = 'version_unsupported'
    missing_catalog_privilege = 'missing_catalog_privilege'
    catalog_view_inaccessible = 'catalog_view_inaccessible'


def run_diagnostics(check: SapHanaCheck):
    HanaDiagnose(check)._run()


def _classify_access_error(error) -> HanaConfigurationError:
    """Map a query exception to a privilege or generic catalog-access diagnostic code."""
    error_lower = str(error).lower()
    if 'insufficient privilege' in error_lower or 'not authorized' in error_lower:
        return HanaConfigurationError.missing_catalog_privilege
    return HanaConfigurationError.catalog_view_inaccessible


class HanaDiagnose:
    def __init__(self, check: SapHanaCheck):
        self._check = check
        self._failed = set()

    def _run(self):
        self._failed = set()
        conn = self._open_probe_connection()
        if conn is None:
            return
        try:
            self._diagnose_version(conn)
            self._diagnose_catalog_access(conn)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _open_probe_connection(self):
        code = HanaConfigurationError.connection_failure
        conn = self._check.get_connection()
        if conn is None:
            self._fail(
                code.value,
                diagnosis="Failed to connect to SAP HANA at {}:{}".format(self._check._server, self._check._port),
                description=DIAGNOSTIC_METADATA[code.value]['description'],
                remediation=DIAGNOSTIC_METADATA[code.value]['remediation'],
            )
            return None
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="Connected to SAP HANA at {}:{}".format(self._check._server, self._check._port),
            category=_CATEGORY,
        )
        return conn

    def _diagnose_version(self, conn):
        code = HanaConfigurationError.version_unsupported
        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute("SELECT VERSION FROM SYS.M_DATABASE")
                row = cursor.fetchone()
        except Exception as e:
            # A failed version query is an access problem, not a version mismatch, so report the
            # privilege/access diagnostic whose remediation matches the real cause.
            access_code = _classify_access_error(e)
            self._fail(
                access_code.value,
                diagnosis="Could not read SAP HANA version from SYS.M_DATABASE: {}".format(e),
                description=DIAGNOSTIC_METADATA[access_code.value]['description'],
                remediation=DIAGNOSTIC_METADATA[access_code.value]['remediation'],
                rawerror=str(e),
            )
            return

        if not row:
            self._fail(
                code.value,
                diagnosis="SYS.M_DATABASE returned no rows",
                description=DIAGNOSTIC_METADATA[code.value]['description'],
                remediation=DIAGNOSTIC_METADATA[code.value]['remediation'],
            )
            return

        version_str = str(row[0]).split()[0]
        try:
            major = int(version_str.split('.')[0])
        except (ValueError, IndexError):
            major = 0

        if major < _MINIMUM_MAJOR_VERSION:
            self._fail(
                code.value,
                diagnosis="SAP HANA version {} is not supported (minimum: {}.x)".format(
                    version_str, _MINIMUM_MAJOR_VERSION
                ),
                description=DIAGNOSTIC_METADATA[code.value]['description'],
                remediation=DIAGNOSTIC_METADATA[code.value]['remediation'],
            )
            return

        self._check.diagnosis.success(
            name=code.value,
            diagnosis="SAP HANA version {} is supported".format(version_str),
            category=_CATEGORY,
        )

    def _diagnose_catalog_access(self, conn):
        for view in _CATALOG_VIEWS:
            self._diagnose_single_view(conn, view)

    def _diagnose_single_view(self, conn, view):
        name = "{}_accessible".format(view.replace('.', '_').lower())
        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute("SELECT COUNT(*) FROM {}".format(view))
                cursor.fetchone()
        except Exception as e:
            code = _classify_access_error(e)
            self._fail(
                name,
                diagnosis="Could not query {}: {}".format(view, e),
                description=DIAGNOSTIC_METADATA[code.value]['description'],
                remediation=DIAGNOSTIC_METADATA[code.value]['remediation'],
                rawerror=str(e),
            )
            return

        self._check.diagnosis.success(
            name=name,
            diagnosis="{} is accessible".format(view),
            category=_CATEGORY,
        )

    def _fail(self, name, diagnosis, description='', remediation='', rawerror=None):
        self._failed.add(name)
        self._check.diagnosis.fail(
            name=name,
            diagnosis=diagnosis,
            category=_CATEGORY,
            description=description,
            remediation=remediation,
            rawerror=rawerror,
        )
