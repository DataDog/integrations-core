# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from datetime import datetime, timedelta, timezone

import pytest

from datadog_checks.active_directory import ActiveDirectoryCheck
from datadog_checks.active_directory.directory import (
    COMPUTER_FILTER,
    USER_FILTER,
    ActiveDirectoryDirectoryCheck,
    build_computer_record,
    build_user_record,
    column_values,
    domain_from_dn,
    escape_filter_value,
    filetime_to_iso,
    guid_to_str,
    nested_members_filter,
    ou_path_from_dn,
    privileged_group_filter,
    sid_to_bytes,
    sid_to_str,
)
from datadog_checks.base.utils.genresources import GenericResourceEvent
from datadog_checks.dev.utils import get_metadata_metrics

DOMAIN_DN = 'DC=corp,DC=example,DC=com'
DOMAIN_SID = 'S-1-5-21-1377283216-344919071-3415362939'
DC1_SERVICE = f'CN=NTDS Settings,CN=DC1,CN=Servers,CN=Default-First-Site-Name,CN=Sites,CN=Configuration,{DOMAIN_DN}'
DC2_SERVICE = f'CN=NTDS Settings,CN=DC2,CN=Servers,CN=Default-First-Site-Name,CN=Sites,CN=Configuration,{DOMAIN_DN}'

# {00112233-4455-6677-8899-aabbccddeeff} in the little-endian byte layout AD stores objectGUID in.
GUID_BYTES = bytes.fromhex('33221100554477668899aabbccddeeff')
GUID_STR = '00112233-4455-6677-8899-aabbccddeeff'
# S-1-5-32-544 (BUILTIN\Administrators) in binary SID form.
ADMINISTRATORS_SID_BYTES = bytes.fromhex('01020000000000052000000020020000')

JDOE_DN = f'CN=jdoe,OU=Engineering,OU=Users,{DOMAIN_DN}'
BOSS_DN = f'CN=boss,OU=Users,{DOMAIN_DN}'
DOMAIN_ADMINS_DN = f'CN=Domain Admins,CN=Users,{DOMAIN_DN}'
UTC = timezone.utc


def guid(n):
    return bytes([n]) * 16


def guid_str(n):
    return guid_to_str(guid(n))


def user_entry(n, dn, **attributes):
    entry = {
        'objectGUID': [guid(n)],
        'objectSid': [sid_to_bytes(f'{DOMAIN_SID}-{1000 + n}')],
        'sAMAccountName': [dn.split(',')[0][3:]],
        'distinguishedName': [dn],
        'userAccountControl': [512],
        'whenCreated': [datetime(2026, 10, 30, 8, 12, 44, tzinfo=UTC)],
    }
    entry.update(attributes)
    return entry


def computer_entry(n, name, **attributes):
    entry = {
        'objectGUID': [guid(n)],
        'distinguishedName': [f'CN={name},CN=Computers,{DOMAIN_DN}'],
        'objectSid': [sid_to_bytes(f'{DOMAIN_SID}-{2000 + n}')],
        'sAMAccountName': [f'{name}$'],
        'dNSHostName': [f'{name.lower()}.corp.example.com'],
        'userAccountControl': [4096],
    }
    entry.update(attributes)
    return entry


class FakeDirectory:
    """Stands in for ADSI. Answers only the queries the crawl is expected to make."""

    def __init__(self, *, server=DC1_SERVICE, pdc=DC1_SERVICE, users=(), computers=(), groups=(), nested=None):
        self.server = server
        self.pdc = pdc
        self.users = list(users)
        self.computers = list(computers)
        self.groups = list(groups)
        self.nested = nested or {}
        self.searches = []

    def read_root_dse(self, attribute):
        return {'defaultNamingContext': DOMAIN_DN, 'dsServiceName': self.server}[attribute]

    def read_object(self, dn, attributes):
        assert dn == DOMAIN_DN
        return {'fSMORoleOwner': [self.pdc], 'objectSid': [sid_to_bytes(DOMAIN_SID)]}

    def search(self, base_dn, ldap_filter, attributes):
        assert base_dn == DOMAIN_DN
        self.searches.append(ldap_filter)
        if ldap_filter == USER_FILTER:
            return iter(self.users)
        if ldap_filter == COMPUTER_FILTER:
            return iter(self.computers)
        if ldap_filter == privileged_group_filter(DOMAIN_SID):
            return iter(self.groups)
        for group_dn, members in self.nested.items():
            if ldap_filter == nested_members_filter(group_dn):
                return iter(members)
        raise AssertionError(f'unexpected search filter {ldap_filter}')


def decode_resources(aggregator):
    resources = []
    for payload in aggregator.get_event_platform_events('genresources', parse_json=False):
        event = GenericResourceEvent()
        event.ParseFromString(payload)
        resources.append(event.resource)
    return resources


@pytest.fixture
def fake_directory(mocker):
    def install(directory):
        mocker.patch('datadog_checks.active_directory.directory.AdsiDirectory', return_value=directory)
        return directory

    return install


@pytest.fixture
def clock(mocker):
    mock_time = mocker.patch('datadog_checks.active_directory.directory.time')
    mock_time.time.return_value = 1_800_000_000
    return mock_time.time


# --- value conversions -------------------------------------------------------------------------


def test_guid_to_str_uses_ad_byte_order():
    # A wrong byte order produces an ID that matches nothing else that reports the same object.
    assert guid_to_str(GUID_BYTES) == GUID_STR


def test_sid_conversion_matches_windows_string_form():
    # The SID string must equal the TargetUserSid Windows writes into logon events.
    assert sid_to_str(ADMINISTRATORS_SID_BYTES) == 'S-1-5-32-544'
    assert sid_to_bytes('S-1-5-32-544') == ADMINISTRATORS_SID_BYTES
    user_sid = f'{DOMAIN_SID}-1104'
    assert sid_to_str(sid_to_bytes(user_sid)) == user_sid


@pytest.mark.parametrize(
    'value, expected',
    [
        pytest.param(None, None, id='attribute_missing'),
        pytest.param(0, None, id='never_zero'),
        pytest.param(0x7FFFFFFFFFFFFFFF, None, id='never_max'),
        pytest.param(116444736000000000, '1970-01-01T00:00:00Z', id='unix_epoch'),
        pytest.param(134380845000000000, '2026-11-02T09:15:00Z', id='recent'),
    ],
)
def test_filetime_to_iso(value, expected):
    assert filetime_to_iso(value) == expected


@pytest.mark.parametrize(
    'dn, domain, ou_path',
    [
        pytest.param(JDOE_DN, 'corp.example.com', 'Users/Engineering', id='nested_ous'),
        pytest.param(f'CN=PC1,CN=Computers,{DOMAIN_DN}', 'corp.example.com', 'Computers', id='container'),
        pytest.param(
            'CN=Doe\\, John,OU=Sales\\, EMEA,DC=corp,DC=example,DC=com',
            'corp.example.com',
            'Sales, EMEA',
            id='escaped_commas',
        ),
        pytest.param(f'CN=root,{DOMAIN_DN}', 'corp.example.com', '', id='domain_root'),
    ],
)
def test_dn_parsing(dn, domain, ou_path):
    assert domain_from_dn(dn) == domain
    assert ou_path_from_dn(dn) == ou_path


def test_escape_filter_value_escapes_ldap_specials():
    # An unescaped "(" in a group name would break or alter the privileged-member query.
    assert escape_filter_value('CN=Ops (tier*0)\\x') == 'CN=Ops \\28tier\\2a0\\29\\5cx'


def test_nested_members_filter_escapes_group_dn():
    # Group DNs may contain parentheses; unescaped they change which users are marked privileged.
    assert nested_members_filter('CN=Ops (EU),DC=corp') == (
        f'(&{USER_FILTER}(memberOf:1.2.840.113556.1.4.1941:=CN=Ops \\28EU\\29,DC=corp))'
    )


def test_column_values_normalizes_adsi_buffers():
    # ADSI returns binary attributes as memoryview; the record builders expect bytes.
    assert column_values([(memoryview(GUID_BYTES), 8), ('jdoe', 3)]) == [GUID_BYTES, 'jdoe']


# --- record mapping ----------------------------------------------------------------------------


def test_build_user_record_full():
    entry = user_entry(
        1,
        JDOE_DN,
        objectSid=[sid_to_bytes(f'{DOMAIN_SID}-1104')],
        lastLogonTimestamp=[134380845000000000],
        pwdLastSet=[134378215640000000],
        memberOf=[DOMAIN_ADMINS_DN],
        adminCount=[1],
        servicePrincipalName=['HTTP/web.corp.example.com'],
        department=['Engineering'],
        title=['SRE'],
        manager=[BOSS_DN],
        userPrincipalName=['jdoe@corp.example.com'],
        mail=['john.doe@example.com'],
        employeeID=['E1234'],
        objectClass=['top', 'person', 'organizationalPerson', 'user'],
        # Secrets must never reach the payload even if the directory returns them.
        unicodePwd=[b'secret'],
        lastLogon=[134380845000000000],
    )
    record = build_user_record(entry, {BOSS_DN.lower(): guid_str(2)}, {guid_str(1): {'Domain Admins'}})

    assert record == {
        'id': guid_str(1),
        'sid': f'{DOMAIN_SID}-1104',
        'account_name': 'jdoe',
        'user_principal_name': 'jdoe@corp.example.com',
        'email': 'john.doe@example.com',
        'employee_id': 'E1234',
        'domain': 'corp.example.com',
        'ou_path': 'Users/Engineering',
        'account': {
            'enabled': True,
            'password_never_expires': False,
            'password_not_required': False,
            'preauth_not_required': False,
        },
        'created_at': '2026-10-30T08:12:44Z',
        'last_logon_at': '2026-11-02T09:15:00Z',
        'password_last_set_at': '2026-10-30T08:12:44Z',
        'groups': {'member_of': [DOMAIN_ADMINS_DN]},
        'privilege': {'is_privileged': True, 'privileged_groups': ['Domain Admins'], 'admin_count': True},
        'service_account': {'service_principal_names': ['HTTP/web.corp.example.com'], 'managed': False},
        'organization': {'department': 'Engineering', 'title': 'SRE', 'manager_id': guid_str(2)},
    }


def test_build_user_record_minimal_entry():
    # A fresh account has no logon, groups, SPNs or org data; the record must still be complete.
    record = build_user_record(user_entry(1, JDOE_DN), {}, {})

    assert record['user_principal_name'] is None
    assert record['email'] is None
    assert record['employee_id'] is None
    assert record['last_logon_at'] is None
    assert record['password_last_set_at'] is None
    assert record['groups'] == {'member_of': []}
    assert record['privilege'] == {'is_privileged': False, 'privileged_groups': [], 'admin_count': False}
    assert record['service_account'] == {'service_principal_names': [], 'managed': False}
    assert record['organization'] == {'department': None, 'title': None, 'manager_id': None}


@pytest.mark.parametrize(
    'when_created',
    [
        pytest.param(datetime(2026, 10, 30, 8, 12, 44, tzinfo=UTC), id='utc'),
        pytest.param(datetime(2026, 10, 30, 10, 12, 44, tzinfo=timezone(timedelta(hours=2))), id='offset'),
        pytest.param(datetime(2026, 10, 30, 8, 12, 44), id='naive_is_utc'),
    ],
)
def test_build_user_record_created_at_is_utc(when_created):
    record = build_user_record(user_entry(1, JDOE_DN, whenCreated=[when_created]), {}, {})
    assert record['created_at'] == '2026-10-30T08:12:44Z'


@pytest.mark.parametrize(
    'uac, expected',
    [
        pytest.param(0x200, {}, id='normal'),
        pytest.param(0x202, {'enabled': False}, id='disabled'),
        pytest.param(0x10200, {'password_never_expires': True}, id='password_never_expires'),
        pytest.param(0x220, {'password_not_required': True}, id='password_not_required'),
        pytest.param(0x400200, {'preauth_not_required': True}, id='preauth_not_required'),
        pytest.param(0x10202, {'enabled': False, 'password_never_expires': True}, id='combined'),
    ],
)
def test_build_user_record_account_flags(uac, expected):
    # Each flag is read from its own userAccountControl bit; a wrong mask hides or invents posture risk.
    defaults = {
        'enabled': True,
        'password_never_expires': False,
        'password_not_required': False,
        'preauth_not_required': False,
    }
    record = build_user_record(user_entry(1, JDOE_DN, userAccountControl=[uac]), {}, {})
    assert record['account'] == {**defaults, **expected}


@pytest.mark.parametrize(
    'admin_count, groups, expected',
    [
        pytest.param(
            None, set(), {'is_privileged': False, 'privileged_groups': [], 'admin_count': False}, id='regular'
        ),
        # AD never clears adminCount when an account leaves a protected group, so it alone is not privilege.
        pytest.param(
            [1], set(), {'is_privileged': False, 'privileged_groups': [], 'admin_count': True}, id='stale_admin_count'
        ),
        pytest.param(
            None,
            {'Domain Admins', 'Backup Operators'},
            {'is_privileged': True, 'privileged_groups': ['Backup Operators', 'Domain Admins'], 'admin_count': False},
            id='nested_groups_sorted',
        ),
    ],
)
def test_build_user_record_privilege(admin_count, groups, expected):
    extra = {'adminCount': admin_count} if admin_count is not None else {}
    record = build_user_record(user_entry(1, JDOE_DN, **extra), {}, {guid_str(1): groups})
    assert record['privilege'] == expected


@pytest.mark.parametrize(
    'object_class, managed',
    [
        pytest.param(['top', 'person', 'organizationalPerson', 'user'], False, id='user'),
        pytest.param(['top', 'user', 'computer', 'msDS-GroupManagedServiceAccount'], True, id='gmsa'),
        pytest.param(['top', 'user', 'computer', 'msDS-ManagedServiceAccount'], True, id='msa'),
    ],
)
def test_build_user_record_managed_service_account(object_class, managed):
    # gMSAs and MSAs are non-human identities even when they have no SPN.
    record = build_user_record(user_entry(1, JDOE_DN, objectClass=object_class), {}, {})
    assert record['service_account']['managed'] is managed


def test_build_user_record_manager_outside_crawl():
    # A manager in another domain is not in the DN map; we report no ID rather than a wrong one.
    record = build_user_record(user_entry(1, JDOE_DN, manager=['CN=x,DC=other,DC=com']), {}, {})
    assert record['organization']['manager_id'] is None


def test_build_user_record_manager_dn_case_insensitive():
    record = build_user_record(user_entry(1, JDOE_DN, manager=[BOSS_DN.upper()]), {BOSS_DN.lower(): guid_str(2)}, {})
    assert record['organization']['manager_id'] == guid_str(2)


def test_build_computer_record_full():
    entry = computer_entry(
        3,
        'WEB1',
        operatingSystem=['Windows Server 2022 Datacenter'],
        operatingSystemVersion=['10.0 (20348)'],
        lastLogonTimestamp=[134380845000000000],
        userAccountControl=[4096 | 0x80000],
        **{'msDS-AllowedToDelegateTo': ['cifs/fs1.corp.example.com']},
    )
    assert build_computer_record(entry) == {
        'id': guid_str(3),
        'sid': f'{DOMAIN_SID}-2003',
        'account_name': 'WEB1$',
        'computer_name': 'WEB1',
        'hostname': 'web1.corp.example.com',
        'domain': 'corp.example.com',
        'ou_path': 'Computers',
        'enabled': True,
        'os': {'name': 'Windows Server 2022 Datacenter', 'version': '10.0 (20348)'},
        'last_logon_at': '2026-11-02T09:15:00Z',
        'delegation': {'unconstrained': True, 'allowed_targets': ['cifs/fs1.corp.example.com']},
    }


def test_build_computer_record_prestaged_account():
    # Pre-staged computer accounts have no hostname, OS or logon until the machine joins.
    entry = computer_entry(3, 'NEW1', userAccountControl=[4098])
    del entry['dNSHostName']
    record = build_computer_record(entry)

    assert record['hostname'] is None
    assert record['enabled'] is False
    assert record['os'] == {'name': None, 'version': None}
    assert record['last_logon_at'] is None
    assert record['delegation'] == {'unconstrained': False, 'allowed_targets': []}


# --- check -------------------------------------------------------------------------------------


def test_routes_directory_instances_to_directory_check():
    check = ActiveDirectoryCheck('active_directory', {}, [{'collect_directory': True}])
    assert isinstance(check, ActiveDirectoryDirectoryCheck)


def test_non_pdc_domain_controller_sends_nothing(aggregator, dd_run_check, fake_directory, clock):
    directory = fake_directory(FakeDirectory(server=DC2_SERVICE, users=[user_entry(1, JDOE_DN)]))
    check = ActiveDirectoryDirectoryCheck('active_directory', {}, [{'collect_directory': True, 'tags': ['team:x']}])
    dd_run_check(check)

    assert directory.searches == []
    assert decode_resources(aggregator) == []
    aggregator.assert_metric('active_directory.directory.is_pdc_emulator', 0, tags=['team:x'])
    aggregator.assert_metric('active_directory.directory.records', count=0)


@pytest.mark.parametrize(
    'instance, ttl',
    [
        pytest.param({}, 3 * 3600, id='default_interval'),
        pytest.param({'min_collection_interval': 7200, 'tags': ['team:x']}, 3 * 7200, id='custom_interval_and_tags'),
    ],
)
def test_pdc_sends_all_users_and_computers(aggregator, dd_run_check, fake_directory, clock, instance, ttl):
    fake_directory(
        FakeDirectory(
            users=[user_entry(1, JDOE_DN, manager=[BOSS_DN]), user_entry(2, BOSS_DN)],
            computers=[computer_entry(3, 'WEB1')],
            groups=[{'distinguishedName': [DOMAIN_ADMINS_DN], 'sAMAccountName': ['Domain Admins']}],
            nested={DOMAIN_ADMINS_DN: [{'objectGUID': [guid(2)]}]},
        )
    )
    check = ActiveDirectoryDirectoryCheck('active_directory', {}, [{'collect_directory': True, **instance}])
    dd_run_check(check)

    resources = {r.key: r for r in decode_resources(aggregator)}
    assert sorted((r.type, k) for k, r in resources.items()) == [
        ('active_directory_computer', guid_str(3)),
        ('active_directory_user', guid_str(1)),
        ('active_directory_user', guid_str(2)),
    ]
    for resource in resources.values():
        assert resource.seen_at.seconds == 1_800_000_000
        assert resource.expire_at.seconds == 1_800_000_000 + ttl

    jdoe = json.loads(resources[guid_str(1)].fields_json)
    boss = json.loads(resources[guid_str(2)].fields_json)
    assert jdoe['account_name'] == 'jdoe'
    assert jdoe['organization']['manager_id'] == guid_str(2)
    assert jdoe['privilege']['is_privileged'] is False
    assert boss['privilege'] == {'is_privileged': True, 'privileged_groups': ['Domain Admins'], 'admin_count': False}

    tags = instance.get('tags', [])
    aggregator.assert_metric('active_directory.directory.is_pdc_emulator', 1, tags=tags)
    aggregator.assert_metric('active_directory.directory.records', 2, tags=tags + ['record_type:active_directory_user'])
    aggregator.assert_metric(
        'active_directory.directory.records', 1, tags=tags + ['record_type:active_directory_computer']
    )
    aggregator.assert_metric('active_directory.directory.crawl.duration', tags=tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_crawls_once_per_interval(aggregator, dd_run_check, fake_directory, clock):
    # Without min_collection_interval the Agent runs the check every 15s; the PDC must not be crawled each time.
    directory = fake_directory(FakeDirectory(users=[user_entry(1, JDOE_DN)]))
    check = ActiveDirectoryDirectoryCheck('active_directory', {}, [{'collect_directory': True}])

    dd_run_check(check)
    crawls_after_first_run = directory.searches.count(USER_FILTER)
    clock.return_value += 3599
    dd_run_check(check)
    assert directory.searches.count(USER_FILTER) == crawls_after_first_run == 1

    clock.return_value += 1
    dd_run_check(check)
    assert directory.searches.count(USER_FILTER) == 2


def test_failed_crawl_is_retried_next_interval(dd_run_check, fake_directory, clock):
    # A failing crawl must surface as a check error but not be retried against the PDC on every 15s run.
    directory = fake_directory(FakeDirectory(users=[user_entry(1, JDOE_DN)]))
    directory.search = lambda *args: (_ for _ in ()).throw(RuntimeError('LDAP unavailable'))
    check = ActiveDirectoryDirectoryCheck('active_directory', {}, [{'collect_directory': True}])

    with pytest.raises(Exception, match='LDAP unavailable'):
        dd_run_check(check)
    clock.return_value += 15
    dd_run_check(check)


def test_pdc_role_moving_moves_collection(aggregator, dd_run_check, fake_directory, clock):
    # After the PDC role is transferred, the old holder must stop sending and the new one start.
    directory = fake_directory(FakeDirectory(users=[user_entry(1, JDOE_DN)]))
    check = ActiveDirectoryDirectoryCheck('active_directory', {}, [{'collect_directory': True}])
    dd_run_check(check)
    assert len(decode_resources(aggregator)) == 1

    aggregator.reset()
    directory.pdc = DC2_SERVICE
    clock.return_value += 3600
    dd_run_check(check)
    assert decode_resources(aggregator) == []
    aggregator.assert_metric('active_directory.directory.is_pdc_emulator', 0)
