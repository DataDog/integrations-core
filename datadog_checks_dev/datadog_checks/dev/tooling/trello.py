# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests


class TrelloClient:
    API_URL = 'https://api.trello.com'
    CREATE_ENDPOINT = API_URL + '/1/cards'

    def __init__(self, config):
        self.auth = {
            'key': config['trello']['key'] or None,
            'token': config['trello']['token'] or None,
        }
        self.team_list_map = {
            'Integrations': '5ae1e3e2c81fff836d00497e',
            'Containers': '5ae1cab495edd80852396c71',
            'Agent': '5ae1e3d62a5167779e65e87d',
        }

    def create_card(self, team, name, body):
        rate_limited = False
        error = None
        response = None

        params = {
            'idList': self.team_list_map[team],
            'name': name,
            'desc': body,
        }
        params.update(self.auth)

        try:
            response = requests.post(self.CREATE_ENDPOINT, params=params)
        except Exception as e:
            error = str(e)
        else:
            try:
                response.raise_for_status()
            except Exception as e:
                error = str(e)

        # Rate limit
        if response:
            rate_limited = response.status_code == 429

        return rate_limited, error, response
