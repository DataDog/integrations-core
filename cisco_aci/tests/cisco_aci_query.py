# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

import requests

# This is a python script that you can use to query a specific
# tenant metric endpoint and includes the login and logout requests.
# You can change the parameters below for your configuration and tenant to query.

# Edit this section. Below is a sample config using the public sandbox:
apic_url = 'sandboxapicdc.cisco.com'
apic_username = 'admin'
apic_password = '!v3G@!4@Y'
tenant = 'infra'
api_path = str.format('/api/mo/uni/tn-{}.json?rsp-subtree-include=stats,no-scoped', tenant)


def apic_login(apic, username, password):
    """APIC login and return session cookie"""
    apic_cookie = {}
    credentials = {'aaaUser': {'attributes': {'name': username, 'pwd': password}}}
    json_credentials = json.dumps(credentials)
    base_url = 'https://' + apic + '/api/aaaLogin.json'

    login_response = requests.post(base_url, data=json_credentials, verify=False)

    login_response_json = json.loads(login_response.text)
    token = login_response_json['imdata'][0]['aaaLogin']['attributes']['token']
    apic_cookie['APIC-Cookie'] = token
    return apic_cookie


def apic_query(apic, path, cookie):
    """APIC 'GET' query and return response"""
    base_url = 'https://' + apic + path

    get_response = requests.get(base_url, cookies=cookie, verify=False)

    return get_response


def apic_logout(apic, cookie):
    """APIC logout and return response"""
    base_url = 'https://' + apic + '/api/aaaLogout.json'

    post_response = requests.post(base_url, cookies=cookie, verify=False)

    return post_response


apic_cookie = apic_login(apic=apic_url, username=apic_username, password=apic_password)
response = apic_query(apic=apic_url, path=api_path, cookie=apic_cookie)
logout_response = apic_logout(apic=apic_url, cookie=apic_cookie)

response_json = json.loads(response.text)

print(json.dumps(response_json, indent=2, sort_keys=True))
