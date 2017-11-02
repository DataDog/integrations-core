#!/usr/bin/env python

import os
import sys
import getopt
import logging
import hashlib
import platform

from requests import Session
from bs4 import BeautifulSoup
import simplejson as json
from zipfile import ZipFile


log = logging.getLogger(__file__)
# logging.basicConfig(level=logging.DEBUG)


ORACLE_DIR_TARGET = 'instantclient'
DL_CONFIGS = "instantclient_config.json"

def oracle_dl(target_url, target_local, sha, destination, username, password):
    if os.path.isfile(target_local):
        log.warn("File exists, will not download")
        return False

    s = Session()
    s.cookies.set('oraclelicense', 'accept-ic_winx8664-cookie', domain='oracle.com')
    s.cookies.set('oraclelicense', 'accept-ic_winx8664-cookie', domain='download.oracle.com')

    login_steptwo_url = 'https://login.oracle.com:443/oaam_server/oamLoginPage.jsp'
    login_form_url = 'https://login.oracle.com/oaam_server/loginAuth.do'

    oam_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'en-US,en;q=0.8'
    }

    response = s.get(target_url, headers=oam_headers, allow_redirects=True)

    soup = BeautifulSoup(response.content, 'html.parser')
    OAM_REQ = soup.find('input', attrs={'name': 'OAM_REQ'})['value']
    token = soup.find('input', attrs={'name': 'tap_token'})['value']
    tap_url = soup.find('input', attrs={'name': 'TapSubmitURL'})['value']

    form = {
        'OAM_REQ': OAM_REQ,
        'tap_token': token,
        'TapSubmitURL': tap_url,
    }
    response = s.post(login_steptwo_url, headers=oam_headers, data=form, allow_redirects=True)

    soup = BeautifulSoup(response.content, 'html.parser')
    fk = soup.find('input', attrs={'name': 'fk'})['value']

    login_form = {
        'fk': fk,
        'clientOffset': 1,
        'userid': username,
        'pass': password,
    }

    login_headers = {
        'Cache-Control': 'max-age=0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'en-US,en;q=0.8'
    }

    response = s.post(login_form_url,
                    headers=login_headers, data=login_form, allow_redirects=True)

    jump_form = {
        'jump': 'false',
        'clientOffset': 1,
    }

    response = s.get('https://login.oracle.com/oaam_server/authJump.do?jump=false',
                    headers=login_headers, data=jump_form, allow_redirects=True)

    soup = BeautifulSoup(response.content, 'html.parser')
    OAM_REQ = soup.find('input', attrs={'name': 'OAM_REQ'})['value']
    token = soup.find('input', attrs={'name': 'oam_tap_token'})['value']

    oam_form = {
        'OAM_REQ': OAM_REQ,
        'oam_tap_token': token,
    }
    response = s.post('https://login.oracle.com:443/oam/server/dap/cred_submit',
                    headers=login_headers, data=oam_form, allow_redirects=True, stream=True)

    hash_sha256 = hashlib.sha256()
    with open(target_local, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                hash_sha256.update(chunk)

    return (hash_sha256.hexdigest() == sha)

def sha256(fname):
    hash_sha256 = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def get_members(zip):
    parts = []
    # get all the path prefixes
    for name in zip.namelist():
        # only check files (not directories)
        if not name.endswith('/'):
            # keep list of path elements (minus filename)
            parts.append(name.split('/')[:-1])
    # now find the common path prefix (if any)
    prefix = os.path.commonprefix(parts)
    if prefix:
        # re-join the path elements
        prefix = '/'.join(prefix) + '/'
    # get the length of the common prefix
    offset = len(prefix)
    # now re-set the filenames
    for zipinfo in zip.infolist():
        name = zipinfo.filename
        # only check files (not directories)
        if len(name) > offset:
            # remove the common prefix
            zipinfo.filename = name[offset:]
            yield zipinfo

def usage():
    print 'usage: {} -a yes|no [-u user | -p pass | -d destination]'.format(sys.argv[0])
    print '\t -a | --agree= : user to oracle SSO'
    print '\t -u | --user= : user to oracle SSO'
    print '\t -p | --pass= : pass to oracle SSO'
    print '\t -d | --dest= : destination to download instantclient'
    print '\t -o | --plat= : platform to download instantclient (linux, darwin, win32)'
    print '\n\n\t You may also specify user ane passwd with ORACLE_USER and ORACLE pass env vars.'


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ha:u:p:d:o:v",
                                   ["help", "agree=", "user=", "pass=", "dest=", "plat="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print str(err)
        usage()
        sys.exit(2)

    username = None
    password = None
    agree = False
    destination = None
    plat = None
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-a", "--agree"):
            agree = True if a.strip().lower() == "yes" else False
        elif o in ("-u", "--user"):
            username = a
        elif o in ("-p", "--pass"):
            password = a
        elif o in ("-d", "--dest"):
            destination = a
        elif o in ("-o", "--plat"):
            plat = a
        else:
            assert False, "unhandled option"

    if not agree:
        print "You must agree to the oracle instantclient terms and conditions to continue."
        usage()
        sys.exit(2)

    if not username:
        username = os.environ.get('ORACLE_USER')
    if not password:
        password = os.environ.get('ORACLE_PASS')
    if not destination:
        destination = os.environ.get('ORACLE_DIR') if 'ORACLE_DIR' in os.environ else os.getcwd()

    if not username or not password:
        print 'Credential env vars not set - quitting'
        usage()
        sys.exit(2)

    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), DL_CONFIGS), "r") as fp:
        configs = json.load(fp)

    pkg_os = plat or platform.system().lower()
    default_version = configs['defaultversion'][pkg_os]

    for pkg in ['basic', 'sdk']:
        target = configs[default_version][pkg_os]['x64'][pkg]['url']
        target_sha256 = configs[default_version][pkg_os]['x64'][pkg]['sha256']


        target_zip = os.path.join(destination, target.split('/')[-1])
        target_dir = os.path.join(destination, ORACLE_DIR_TARGET)

        if os.path.isdir(target_dir):
            log.warn('instantclient folder contents will be overwritten')

        try:
            if not os.path.isfile(target_zip):
                if oracle_dl(target, target_zip, target_sha256, destination, username, password):
                    print "download successful!"
                else:
                    print "unable to download artifact or artifact corrupt"
                    sys.exit(1)
            elif sha256(target_zip) is not target_sha256:
                print "existing artifacts corrupt, please delete and try again"
                sys.exit(1)

            zip = ZipFile(target_zip)
            zip.extractall(target_dir, get_members(zip))
        except Exception:
            log.exception("There was a problem downloading the target")

    print 'InstantClient installation complete.'



if __name__ == "__main__":
    main()
