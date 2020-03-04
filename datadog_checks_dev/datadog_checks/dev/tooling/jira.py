# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import requests
from requests.auth import HTTPBasicAuth


class JiraClient:
    API_URL = 'https://datadoghq.atlassian.net/rest/api'
    CREATE_ENDPOINT = API_URL + '/3/issue'

    def __init__(self, config):
        jira_email = config['jira']['user']
        jira_token = config['jira']['token']

        self.auth = HTTPBasicAuth(jira_email, jira_token)
        self.team_list_map = {
            'Containers': '21',
            'Core': '31',
            'Integrations': '41',
            'Logs': '71',
            'Platform': '51',
            'Networks': '171',
            'Processes': '181',
            'Trace': '61',
        }
        self.label_team_map = {
            'team/agent-apm': 'Trace',
            'team/agent-core': 'Core',
            'team/agent-platform': 'Platform',
            'team/networks': 'Networks',
            'team/processes': 'Processes',
            'team/containers': 'Containers',
            'team/integrations': 'Integrations',
            'team/logs': 'Logs',
        }

    # We will need two API calls until this is added: https://jira.atlassian.com/browse/JRACLOUD-69559?_ga=2.62950895.1343692979.1578939312-1018831208.1578519746 # noqa
    def move_column(self, team, issue_key):
        rate_limited = False
        error = None
        url = f'{self.CREATE_ENDPOINT}/{issue_key}/transitions'

        # Documentation to transition an issue's status/column: https://developer.atlassian.com/cloud/jira/platform/rest/v3/?_ga=2.39263651.1896629564.1578666825-1018831208.1578519746#api-rest-api-3-issue-issueIdOrKey-transitions-post # noqa
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

    def create_issue(self, team, name, body, member=None):
        rate_limited = False
        error = None
        response = None

        # documentation to create a Jira issue: https://developer.atlassian.com/cloud/jira/platform/rest/v3/?_ga=2.39263651.1896629564.1578666825-1018831208.1578519746#api-rest-api-3-issue-post # noqa
        data = {
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

        if member:
            data['fields']['assignee'] = {"id": member}

        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        try:
            response = requests.post(self.CREATE_ENDPOINT, data=json.dumps(data), auth=self.auth, headers=headers)
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
