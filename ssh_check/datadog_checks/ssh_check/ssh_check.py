# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import time
from collections import namedtuple

import paramiko

from datadog_checks.base.checks import AgentCheck

# Example ssh remote version: http://supervisord.org/changes.html
#   - SSH-2.0-OpenSSH_8.1
SSH_REMOTE_VERSION_PATTERN = re.compile(
    r"""
    ^.*_
    (?P<major>0|[1-9]\d*)
    \.
    (?P<minor>0|[1-9]\d*)
    (?P<release>p[1-9]\d*)?
    """,
    re.VERBOSE,
)


class CheckSSH(AgentCheck):
    SSH_SERVICE_CHECK_NAME = 'ssh.can_connect'
    SFTP_SERVICE_CHECK_NAME = 'sftp.can_connect'

    OPTIONS = [
        ('host', True, None, str),
        ('port', False, 22, int),
        ('username', True, None, str),
        ('password', False, None, str),
        ('private_key_file', False, None, str),
        ('private_key_type', False, 'rsa', str),
        ('sftp_check', False, True, bool),
        ('add_missing_keys', False, False, bool),
    ]

    Config = namedtuple(
        'Config',
        [
            'host',
            'port',
            'username',
            'password',
            'private_key_file',
            'private_key_type',
            'sftp_check',
            'add_missing_keys',
        ],
    )

    def _load_conf(self, instance):
        params = []
        for option, required, default, expected_type in self.OPTIONS:
            value = instance.get(option)
            if required and (not value or type(value) != expected_type):
                raise Exception("Please specify a valid {0}".format(option))

            if value is None or type(value) != expected_type:
                self.log.debug("Bad or missing value for %s parameter. Using default", option)
                value = default

            params.append(value)
        return self.Config._make(params)

    def check(self, instance):
        conf = self._load_conf(instance)
        tags = instance.get('tags', [])
        tags.append("instance:{0}-{1}".format(conf.host, conf.port))

        private_key = None

        if conf.private_key_file is not None:
            try:
                if conf.private_key_type == 'ecdsa':
                    private_key = paramiko.ECDSAKey.from_private_key_file(conf.private_key_file)
                else:
                    private_key = paramiko.RSAKey.from_private_key_file(conf.private_key_file)
            except IOError:
                self.warning("Unable to find private key file: %s", conf.private_key_file)
            except paramiko.ssh_exception.PasswordRequiredException:
                self.warning("Private key file is encrypted but no password was given")
            except paramiko.ssh_exception.SSHException:
                self.warning("Private key file is invalid")

        client = paramiko.SSHClient()
        if conf.add_missing_keys:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.load_system_host_keys()

        exception_message = "No errors occured"
        try:
            # Try to connect to check status of SSH
            try:
                client.connect(
                    conf.host, port=conf.port, username=conf.username, password=conf.password, pkey=private_key
                )
                self.service_check(self.SSH_SERVICE_CHECK_NAME, AgentCheck.OK, tags=tags, message=exception_message)

            except Exception as e:
                exception_message = str(e)
                status = AgentCheck.CRITICAL
                self.service_check(self.SSH_SERVICE_CHECK_NAME, status, tags=tags, message=exception_message)
                if conf.sftp_check:
                    self.service_check(self.SFTP_SERVICE_CHECK_NAME, status, tags=tags, message=exception_message)
                raise

            self._collect_metadata(client)

            # Open sftp session on the existing connection to check status of SFTP
            if conf.sftp_check:
                try:
                    sftp = client.open_sftp()
                    # Check response time of SFTP
                    start_time = time.time()
                    sftp.listdir('.')
                    status = AgentCheck.OK
                    end_time = time.time()
                    time_taken = end_time - start_time
                    self.gauge('sftp.response_time', time_taken, tags=tags)

                except Exception as e:
                    exception_message = str(e)
                    status = AgentCheck.CRITICAL

                if exception_message is None:
                    exception_message = "No errors occured"

                self.service_check(self.SFTP_SERVICE_CHECK_NAME, status, tags=tags, message=exception_message)
        finally:
            # Always close the client, failure to do so leaks one thread per connection left open
            client.close()

    def _collect_metadata(self, client):
        try:
            version = client.get_transport().remote_version
        except Exception as e:
            self.log.warning("Error collecting version: %s", e)
            return

        if 'OpenSSH' in version:
            flavor = 'OpenSSH'
        else:
            flavor = 'unknown'

        self.log.debug('Version collected: %s, flavor: %s', version, flavor)

        self.set_metadata('version', version, scheme='regex', pattern=SSH_REMOTE_VERSION_PATTERN)
        self.set_metadata('flavor', flavor)
