# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import requests
from requests.auth import HTTPBasicAuth


class JiraClient:
    API_URL = 'https://datadoghq.atlassian.net/rest/api'
    CREATE_ENDPOINT = API_URL + '/3/issue'

    def __init__(self, config):
        self.auth = HTTPBasicAuth(config['jira']['user'] or None, config['jira']['token'] or None)
        self.team_list_map = {
            'Containers': '21',
            'Core': '31',
            'Integrations': '41',
            'Logs': '71',
            'Platform': '51',
            'Process': '81',
            'Trace': '61',
        }
        self.label_team_map = {
            'team/agent-apm': 'Trace',
            'team/agent-core': 'Core',
            'team/agent-platform': 'Platform',
            'team/burrito': 'Process',
            'team/containers': 'Containers',
            'team/integrations': 'Integrations',
            'team/logs': 'Logs',
        }

    def move_column(self, team, issue_key):
        rate_limited = False
        error = None
        url = '{}/{}/transitions'.format(self.CREATE_ENDPOINT, issue_key)

        data = json.dumps({'transition': {'id': self.team_list_map[team]}})

        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        try:
            response = requests.post(url, data=data, auth=self.auth, headers=headers)
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

    def create_issue(self, team, name, body):
        rate_limited = False
        error = None
        response = None

        data = json.dumps(
            {
                'fields': {
                    'project': {'key': 'AR'},
                    'summary': name,
                    'description': {
                        'type': 'doc',
                        'version': 1,
                        'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': body}]}],
                    },
                    'issuetype': {'name': 'Task'},
                }
            }
        )
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        try:
            response = requests.post(self.CREATE_ENDPOINT, data=data, auth=self.auth, headers=headers)
            issue_key = response.json().get('key')
            rate_limited, error, resp = self.move_column(team, issue_key)
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
