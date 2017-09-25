#!/usr/bin/env python

import pexpect
import os
import sys
import getopt
import platform


TARGET = 'instantclient'

def usage():
    print 'usage: {} -a yes|no [-u user | -p pass | -d destination]'.format(sys.argv[0])
    print '\t -a | --agree= : user to oracle SSO'
    print '\t -u | --user= : user to oracle SSO'
    print '\t -p | --pass= : pass to oracle SSO'
    print '\t -d | --dest= : destination to download instantclient'
    print '\n\n\t You may also specify user ane passwd with ORACLE_USER and ORACLE pass env vars.'

def executable_in_path(cmd):
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        cmd_candidate = os.path.join(directory, cmd)
        if os.path.exists(cmd_candidate):
            return True

    return False

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ha:u:p:d:v",
                                   ["help", "agree=", "user=", "pass=", "dest="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print str(err)
        usage()
        sys.exit(2)

    username = None
    password = None
    agree = False
    destination = None
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

    if not executable_in_path('npm'):
        print 'npm required to continue. Please install npm or otherwise download instantclient manually.'
        sys.exit(-1)

    if os.path.isdir(os.path.join(destination, TARGET)):
        print 'instantclient already installed or conflicting directory present - quitting'
        sys.exit(0)


    npm = pexpect.spawnu('npm install --prefix {} instantclient'.format(destination))
    npm.logfile = sys.stdout

    npm.expect(u'Press \(Y\) to Install, anything else to Cancel\? ', timeout=120)
    npm.sendline('Y')
    npm.expect(u'Press \(Y\) to Accept the License Agreement, anything else to Cancel\? ')
    npm.sendline('Y')
    npm.logfile = None

    npm.expect(u'Please enter your username: ')
    npm.sendline(username)
    npm.expect(u'Please enter your password: ')
    npm.sendline(password)
    npm.expect(u'Directory .* created.', timeout=120)
    sys.stdout.flush()
    npm.logfile = sys.stdout
    if 'linux' in platform.system().lower():
        npm.expect(u'instantclient@', timeout=120)

    try:
        npm.expect(pexpect.EOF, timeout=120)
    except Exception:
        pass
    finally:
        sys.stdout.flush()

    print 'InstantClient installation complete.'


if __name__ == "__main__":
    main()
