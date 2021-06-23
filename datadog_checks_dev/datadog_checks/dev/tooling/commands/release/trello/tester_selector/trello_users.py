# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime
from typing import Dict, List, cast

from .....trello import TrelloClient
from ....console import echo_info
from .cache import Cache


class TrelloUser:
    def __init__(self, data: Dict[str, object]):
        self.id = cast(str, data['id_member'])
        self.full_name = cast(str, data['full_name'])
        self.username = cast(str, data['username'])


class TrelloUsers:
    """
    Store a collection of Trello users
    """

    def __init__(self, trello: TrelloClient, app_dir: str, cache_expiration: datetime):
        self.__trello = trello
        # Use a cache to avoid API Rate Limits
        self.__user_cache = Cache(app_dir, 'trello_user', cache_expiration)

    def get_users(self) -> List[TrelloUser]:
        trello_users = cast(Dict[str, Dict[str, object]], self.__user_cache.get_value())
        if not trello_users:
            trello_users = {}
        membership = self.__trello.get_membership()
        for m in membership:
            if not m['deactivated']:
                id_member = m['idMember']
                if id_member not in trello_users:
                    member = self.__trello.get_member(id_member)
                    fullname = member['fullName']
                    echo_info(f'Getting information for user {fullname}')
                    trello_users[id_member] = {
                        'id_member': id_member,
                        'full_name': fullname,
                        'username': member['username'],
                    }
        self.__user_cache.set_value(trello_users)
        return [TrelloUser(user) for user in trello_users.values()]
