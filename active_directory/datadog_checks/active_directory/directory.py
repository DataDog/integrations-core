# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Send Active Directory user and computer records as generic resources.

Only the domain controller holding the PDC emulator role collects, so each domain is read once.
Every crawl is a full snapshot: change detection happens downstream, and records expire after
`EXPIRY_INTERVALS` missed crawls, which is how deleted objects drop out.
"""

import re
import struct
import time
import uuid
from collections import defaultdict
from collections.abc import Iterator
from datetime import datetime, timezone

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.genresources import INCLUDE_ALL

DEFAULT_CRAWL_INTERVAL = 3600
EXPIRY_INTERVALS = 3
PAGE_SIZE = 1000

USER_TYPE = 'active_directory_user'
COMPUTER_TYPE = 'active_directory_computer'

# People, plus group managed and standalone managed service accounts, which are non-human identities
# whose objectCategory is not `person`.
USER_FILTER = (
    '(|(&(objectCategory=person)(objectClass=user))'
    '(objectClass=msDS-GroupManagedServiceAccount)(objectClass=msDS-ManagedServiceAccount))'
)
MANAGED_SERVICE_ACCOUNT_CLASSES = {'msds-groupmanagedserviceaccount', 'msds-managedserviceaccount'}
COMPUTER_FILTER = '(objectCategory=computer)'

# Explicit allow-list of attributes read from the directory. Secrets and non-replicated values
# (`lastLogon`, `badPwdCount`) are deliberately absent.
USER_ATTRIBUTES = [
    'objectGUID',
    'objectSid',
    'objectClass',
    'sAMAccountName',
    'userPrincipalName',
    'mail',
    'employeeID',
    'givenName',
    'sn',
    'displayName',
    'physicalDeliveryOfficeName',
    'distinguishedName',
    'userAccountControl',
    # Computed on request, so it is only returned when listed explicitly.
    'msDS-User-Account-Control-Computed',
    'accountExpires',
    'whenCreated',
    'lastLogonTimestamp',
    'pwdLastSet',
    'memberOf',
    'adminCount',
    'servicePrincipalName',
    'department',
    'title',
    'manager',
]
COMPUTER_ATTRIBUTES = [
    'objectGUID',
    'objectSid',
    'sAMAccountName',
    'name',
    'distinguishedName',
    'dNSHostName',
    'userAccountControl',
    'whenCreated',
    'operatingSystem',
    'operatingSystemVersion',
    'lastLogonTimestamp',
    'msDS-AllowedToDelegateTo',
]

# https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/useraccountcontrol-manipulate-account-properties
UAC_ACCOUNTDISABLE = 0x2
UAC_PASSWD_NOTREQD = 0x20
UAC_DONT_EXPIRE_PASSWORD = 0x10000
UAC_TRUSTED_FOR_DELEGATION = 0x80000
UAC_DONT_REQ_PREAUTH = 0x400000
UAC_SERVER_TRUST_ACCOUNT = 0x2000  # domain controller
UAC_PARTIAL_SECRETS_ACCOUNT = 0x4000000  # read-only domain controller
# Bit of msDS-User-Account-Control-Computed: lockoutTime stays set after a lockout expires, this does not.
UAC_COMPUTED_LOCKOUT = 0x10

# Well-known privileged groups, identified by SID because group names are localized.
# Domain Admins, Schema Admins, Enterprise Admins (relative to the domain SID).
PRIVILEGED_DOMAIN_RIDS = (512, 518, 519)
# Administrators, Account Operators, Server Operators, Print Operators, Backup Operators.
PRIVILEGED_BUILTIN_SIDS = ('S-1-5-32-544', 'S-1-5-32-548', 'S-1-5-32-549', 'S-1-5-32-550', 'S-1-5-32-551')

# LDAP_MATCHING_RULE_IN_CHAIN: the server resolves nested group membership.
IN_CHAIN_RULE = '1.2.840.113556.1.4.1941'

# FILETIME values AD uses to mean "never".
FILETIME_NEVER = (0, 0x7FFFFFFFFFFFFFFF)
FILETIME_EPOCH_OFFSET = 116444736000000000  # 100ns intervals between 1601-01-01 and 1970-01-01

DN_SPLIT = re.compile(r'(?<!\\),')


def guid_to_str(value: bytes) -> str:
    return str(uuid.UUID(bytes_le=value))


def sid_to_str(value: bytes) -> str:
    revision, count = value[0], value[1]
    authority = int.from_bytes(value[2:8], 'big')
    sub_authorities = struct.unpack(f'<{count}I', value[8 : 8 + 4 * count])
    return '-'.join(['S', str(revision), str(authority), *map(str, sub_authorities)])


def sid_to_bytes(value: str) -> bytes:
    _, revision, authority, *sub_authorities = value.split('-')
    return (
        bytes([int(revision), len(sub_authorities)])
        + int(authority).to_bytes(6, 'big')
        + struct.pack(f'<{len(sub_authorities)}I', *map(int, sub_authorities))
    )


def filetime_to_iso(value: int | None) -> str | None:
    if value is None or value in FILETIME_NEVER:
        return None
    seconds = (value - FILETIME_EPOCH_OFFSET) // 10_000_000
    return datetime.fromtimestamp(seconds, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def datetime_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _dn_components(dn: str) -> list[tuple[str, str]]:
    components = []
    for rdn in DN_SPLIT.split(dn):
        attribute, _, value = rdn.partition('=')
        components.append((attribute.strip().upper(), re.sub(r'\\(.)', r'\1', value)))
    return components


def domain_from_dn(dn: str) -> str:
    return '.'.join(value for attribute, value in _dn_components(dn) if attribute == 'DC')


def ou_path_from_dn(dn: str) -> str:
    """Return the object's containers from the domain root down, e.g. `Users/Engineering`."""
    parents = [value for attribute, value in _dn_components(dn)[1:] if attribute != 'DC']
    return '/'.join(reversed(parents))


def escape_filter_value(value: str) -> str:
    """Escape a value for use in an LDAP filter (RFC 4515)."""
    return ''.join(f'\\{ord(c):02x}' if c in '\\*()\0' else c for c in value)


def _escape_bytes(value: bytes) -> str:
    return ''.join(f'\\{b:02x}' for b in value)


def privileged_group_filter(domain_sid: str) -> str:
    sids = [f'{domain_sid}-{rid}' for rid in PRIVILEGED_DOMAIN_RIDS] + list(PRIVILEGED_BUILTIN_SIDS)
    clauses = ''.join(f'(objectSid={_escape_bytes(sid_to_bytes(sid))})' for sid in sids)
    return f'(&(objectCategory=group)(|{clauses}))'


def nested_members_filter(group_dn: str) -> str:
    return f'(&{USER_FILTER}(memberOf:{IN_CHAIN_RULE}:={escape_filter_value(group_dn)}))'


def crossref_filter(domain_dn: str) -> str:
    """Match the domain's entry under `CN=Partitions`, which holds its NetBIOS name."""
    return f'(&(objectClass=crossRef)(nCName={escape_filter_value(domain_dn)}))'


def column_values(values: list[tuple[object, int]]) -> list:
    """Unwrap ADSI `(value, type)` pairs, converting binary buffers to bytes."""
    return [bytes(value) if isinstance(value, memoryview) else value for value, _ in values]


def _first(entry: dict, attribute: str):
    values = entry.get(attribute)
    return values[0] if values else None


def build_user_record(
    entry: dict,
    guid_by_dn: dict[str, str],
    privileged_groups: dict[str, set[str]],
    domain_netbios_name: str | None = None,
) -> dict:
    dn = _first(entry, 'distinguishedName')
    user_id = guid_to_str(_first(entry, 'objectGUID'))
    groups = sorted(privileged_groups.get(user_id, ()))
    manager = _first(entry, 'manager')
    uac = _first(entry, 'userAccountControl')
    object_classes = {value.lower() for value in entry.get('objectClass', [])}
    return {
        'id': user_id,
        'sid': sid_to_str(_first(entry, 'objectSid')),
        'account_name': _first(entry, 'sAMAccountName'),
        'user_principal_name': _first(entry, 'userPrincipalName'),
        'email': _first(entry, 'mail'),
        'employee_id': _first(entry, 'employeeID'),
        'given_name': _first(entry, 'givenName'),
        'surname': _first(entry, 'sn'),
        'display_name': _first(entry, 'displayName'),
        'domain': domain_from_dn(dn),
        'domain_netbios_name': domain_netbios_name,
        'ou_path': ou_path_from_dn(dn),
        'account': {
            'enabled': not uac & UAC_ACCOUNTDISABLE,
            'locked': bool((_first(entry, 'msDS-User-Account-Control-Computed') or 0) & UAC_COMPUTED_LOCKOUT),
            'expires_at': filetime_to_iso(_first(entry, 'accountExpires')),
            'password_never_expires': bool(uac & UAC_DONT_EXPIRE_PASSWORD),
            'password_not_required': bool(uac & UAC_PASSWD_NOTREQD),
            'preauth_not_required': bool(uac & UAC_DONT_REQ_PREAUTH),
        },
        'created_at': datetime_to_iso(_first(entry, 'whenCreated')),
        'last_logon_at': filetime_to_iso(_first(entry, 'lastLogonTimestamp')),
        'password_last_set_at': filetime_to_iso(_first(entry, 'pwdLastSet')),
        'groups': {'member_of': list(entry.get('memberOf', []))},
        # adminCount is reported separately: AD never clears it when an account leaves a protected group.
        'privilege': {
            'is_privileged': bool(groups),
            'privileged_groups': groups,
            'admin_count': _first(entry, 'adminCount') == 1,
        },
        'service_account': {
            'service_principal_names': list(entry.get('servicePrincipalName', [])),
            'managed': bool(object_classes & MANAGED_SERVICE_ACCOUNT_CLASSES),
        },
        'organization': {
            'department': _first(entry, 'department'),
            'title': _first(entry, 'title'),
            'office': _first(entry, 'physicalDeliveryOfficeName'),
            'manager_id': guid_by_dn.get(manager.lower()) if manager else None,
        },
    }


def build_computer_record(entry: dict, domain_netbios_name: str | None = None) -> dict:
    dn = _first(entry, 'distinguishedName')
    uac = _first(entry, 'userAccountControl')
    if uac & UAC_SERVER_TRUST_ACCOUNT:
        role = 'domain_controller'
    elif uac & UAC_PARTIAL_SECRETS_ACCOUNT:
        role = 'read_only_domain_controller'
    else:
        role = 'member'
    return {
        'id': guid_to_str(_first(entry, 'objectGUID')),
        'sid': sid_to_str(_first(entry, 'objectSid')),
        # `NAME$`, as machine accounts appear in logon events.
        'account_name': _first(entry, 'sAMAccountName'),
        # Always set, unlike dNSHostName, which stays empty until a machine joins the domain.
        'computer_name': _first(entry, 'name'),
        'hostname': _first(entry, 'dNSHostName'),
        'domain': domain_from_dn(dn),
        'domain_netbios_name': domain_netbios_name,
        'ou_path': ou_path_from_dn(dn),
        'role': role,
        'created_at': datetime_to_iso(_first(entry, 'whenCreated')),
        'enabled': not uac & UAC_ACCOUNTDISABLE,
        'os': {'name': _first(entry, 'operatingSystem'), 'version': _first(entry, 'operatingSystemVersion')},
        'last_logon_at': filetime_to_iso(_first(entry, 'lastLogonTimestamp')),
        'delegation': {
            'unconstrained': bool(uac & UAC_TRUSTED_FOR_DELEGATION),
            'allowed_targets': list(entry.get('msDS-AllowedToDelegateTo', [])),
        },
    }


class AdsiDirectory:
    """Reads the local domain controller through ADSI, authenticated as the Agent's own Windows account."""

    def __init__(self):
        import win32api
        import win32con

        self._server = win32api.GetComputerNameEx(win32con.ComputerNameDnsFullyQualified)

    def read_root_dse(self, attribute: str) -> str:
        from win32com import adsi

        return adsi.ADsGetObject(f'LDAP://{self._server}/RootDSE').Get(attribute)

    def read_object(self, dn: str, attributes: list[str]) -> dict:
        from win32com.adsi import adsicon

        return next(self._search(dn, '(objectClass=*)', attributes, adsicon.ADS_SCOPE_BASE), {})

    def search(self, base_dn: str, ldap_filter: str, attributes: list[str]) -> Iterator[dict]:
        from win32com.adsi import adsicon

        return self._search(base_dn, ldap_filter, attributes, adsicon.ADS_SCOPE_SUBTREE)

    def _search(self, base_dn: str, ldap_filter: str, attributes: list[str], scope: int) -> Iterator[dict]:
        from win32com import adsi
        from win32com.adsi import adsicon

        searcher = adsi.ADsGetObject(f'LDAP://{self._server}/{base_dn}', adsi.IID_IDirectorySearch)
        searcher.SetSearchPreference(
            [
                (adsicon.ADS_SEARCHPREF_SEARCH_SCOPE, (scope,)),
                (adsicon.ADS_SEARCHPREF_PAGESIZE, (PAGE_SIZE,)),
                # Child domains have their own PDC emulator; never follow referrals into them.
                (adsicon.ADS_SEARCHPREF_CHASE_REFERRALS, (adsicon.ADS_CHASE_REFERRALS_NEVER,)),
            ]
        )
        handle = searcher.ExecuteSearch(ldap_filter, attributes)
        try:
            while searcher.GetNextRow(handle) != adsicon.S_ADS_NOMORE_ROWS:
                entry = {}
                for attribute in attributes:
                    try:
                        _, _, values = searcher.GetColumn(handle, attribute)
                    except adsi.error as e:
                        if e.hresult != adsicon.E_ADS_COLUMN_NOT_SET:
                            raise
                        continue
                    entry[attribute] = column_values(values)
                yield entry
        finally:
            searcher.CloseSearchHandle(handle)


class ActiveDirectoryDirectoryCheck(AgentCheck):
    __NAMESPACE__ = 'active_directory'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        # The Agent runs the check every 15s unless `min_collection_interval` is set, so the crawl
        # interval is enforced here to keep the default at one crawl per hour.
        self._interval = int(self.instance.get('min_collection_interval', DEFAULT_CRAWL_INTERVAL))
        self._tags = list(self.instance.get('tags', []))
        self._last_crawl = None
        self._directory = None

    def check(self, _):
        now = int(time.time())
        if self._last_crawl is not None and now - self._last_crawl < self._interval:
            return
        # Set before crawling so a failing crawl is retried next interval, not on every run.
        self._last_crawl = now

        if self._directory is None:
            self._directory = AdsiDirectory()

        import pythoncom

        # The Agent runs checks on varying worker threads, and ADSI needs COM initialized on the
        # calling thread; without it ADsGetObject fails with MK_E_SYNTAX ("Invalid syntax").
        pythoncom.CoInitialize()
        try:
            self._crawl(self._directory, now)
        finally:
            pythoncom.CoUninitialize()

    def _crawl(self, directory, now: int):
        domain_dn = directory.read_root_dse('defaultNamingContext')
        server = directory.read_root_dse('dsServiceName')
        domain = directory.read_object(domain_dn, ['fSMORoleOwner', 'objectSid'])
        pdc = _first(domain, 'fSMORoleOwner')
        is_pdc = bool(pdc) and pdc.lower() == server.lower()
        self.gauge('directory.is_pdc_emulator', int(is_pdc), tags=self._tags)
        if not is_pdc:
            self.log.debug('Skipping directory collection: this domain controller is not the PDC emulator')
            return

        expire_at = now + EXPIRY_INTERVALS * self._interval
        domain_sid = sid_to_str(_first(domain, 'objectSid'))
        config_dn = directory.read_root_dse('configurationNamingContext')
        crossref = next(directory.search(f'CN=Partitions,{config_dn}', crossref_filter(domain_dn), ['nETBIOSName']), {})
        netbios_name = _first(crossref, 'nETBIOSName')

        privileged_groups = defaultdict(set)
        groups = directory.search(
            domain_dn, privileged_group_filter(domain_sid), ['distinguishedName', 'sAMAccountName']
        )
        for group in groups:
            members = directory.search(
                domain_dn, nested_members_filter(_first(group, 'distinguishedName')), ['objectGUID']
            )
            for member in members:
                privileged_groups[guid_to_str(_first(member, 'objectGUID'))].add(_first(group, 'sAMAccountName'))

        users = list(directory.search(domain_dn, USER_FILTER, USER_ATTRIBUTES))
        guid_by_dn = {_first(u, 'distinguishedName').lower(): guid_to_str(_first(u, 'objectGUID')) for u in users}
        for entry in users:
            self._submit(
                USER_TYPE, build_user_record(entry, guid_by_dn, privileged_groups, netbios_name), now, expire_at
            )

        computers = 0
        for entry in directory.search(domain_dn, COMPUTER_FILTER, COMPUTER_ATTRIBUTES):
            self._submit(COMPUTER_TYPE, build_computer_record(entry, netbios_name), now, expire_at)
            computers += 1

        self.gauge('directory.records', len(users), tags=self._tags + [f'record_type:{USER_TYPE}'])
        self.gauge('directory.records', computers, tags=self._tags + [f'record_type:{COMPUTER_TYPE}'])
        self.gauge('directory.crawl.duration', time.time() - now, tags=self._tags)

    def _submit(self, record_type: str, record: dict, seen_at: int, expire_at: int):
        # Records are built field by field from the attribute allow-lists above, never from raw entries.
        self.submit_generic_resource(
            type=record_type, key=record['id'], fields=record, include=INCLUDE_ALL, seen_at=seen_at, expire_at=expire_at
        )
