# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from mock import MagicMock

from datadog_checks.dev.tooling.trello import TrelloClient


def test_get_board_members(monkeypatch):
    client = TrelloClient({'trello': {'token': 'my-token', 'key': 'my-key'}})

    mock_response_memberships = MagicMock()
    mock_response_memberships.json.return_value = [
        {"deactivated": False, "idMember": "id1", "memberType": "normal", "unconfirmed": False},
        {"deactivated": False, "idMember": "id2", "memberType": "normal", "unconfirmed": False},
        {"deactivated": True, "idMember": "id3", "memberType": "normal", "unconfirmed": False},
    ]
    mock_response_memberships.headers = {"Content-Type": "application/json"}

    mock_response_members = MagicMock()
    mock_response_members.json.return_value = [
        {"fullName": "first.user", "id": "id1", "username": "first_user"},
        {"fullName": "sec.user", "id": "id2", "username": "second_user"},
        {"fullName": "d.user", "id": "id3", "username": "deactivated_user"},
    ]
    mock_response_members.headers = {"Content-Type": "application/json"}

    def mock_request(url, *args, **kwargs):
        if url == client.MEMBERSHIP_ENDPOINT:
            return mock_response_memberships
        elif url == client.BOARD_MEMBERS_ENDPOINT:
            return mock_response_members

    monkeypatch.setattr('requests.get', MagicMock(side_effect=mock_request))

    members = client.get_board_members()

    assert members == [
        {"fullName": "first.user", "id": "id1", "username": "first_user"},
        {"fullName": "sec.user", "id": "id2", "username": "second_user"},
    ]
