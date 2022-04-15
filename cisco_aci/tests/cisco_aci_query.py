import json
import requests

# Edit this section
apic_url = 'URL.com'
apic_username = 'USERNAME'
apic_password = 'PASSWORD'
api_path = '/api/mo/uni/tn-infra.json?rsp-subtree-include=stats,no-scoped'  # This queries the `infra` tenant


def apic_login(apic, username, password):
    """ APIC login and return session cookie """
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
    """ APIC 'GET' query and return response """
    base_url = 'https://' + apic + path

    get_response = requests.get(base_url, cookies=cookie, verify=False)

    return get_response


def apic_logout(apic, cookie):
    """ APIC logout and return response """
    base_url = 'https://' + apic + '/api/aaaLogout.json'

    post_response = requests.post(base_url, cookies=cookie, verify=False)

    return post_response


apic_cookie = apic_login(apic=apic_url, username=apic_username, password=apic_password)
response = apic_query(apic=apic_url, path=api_path, cookie=apic_cookie)
logout_response = apic_logout(apic=apic_url, cookie=apic_cookie)

response_json = json.loads(response.text)

print(response_json)
