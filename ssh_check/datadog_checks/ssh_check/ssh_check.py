# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import time

import paramiko

from datadog_checks.base import AgentCheck, is_affirmative

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

    def __init__(self, name, init_config, instances):
        super(CheckSSH, self).__init__(name, init_config, instances)
        self.host = self.instance['host']
        self.port = int(self.instance.get('port', 22))
        self.username = self.instance['username']
        self.password = self.instance.get('password')
        self.private_key_file = self.instance.get('private_key_file')
        self.private_key_type = self.instance.get('private_key_type', 'rsa')
        self.sftp_check = is_affirmative(self.instance.get('sftp_check', True))
        self.add_missing_keys = is_affirmative(self.instance.get('add_missing_keys'))
        self.base_tags = self.instance.get('tags', [])
        self.base_tags.append("instance:{0}-{1}".format(self.host, self.port))

    def check(self, _):
        private_key = None

        if self.private_key_file is not None:
            try:
                if self.private_key_type == 'ecdsa':
                    private_key = paramiko.ECDSAKey.from_private_key_file(self.private_key_file, password=self.password)
                else:
                    private_key = paramiko.RSAKey.from_private_key_file(self.private_key_file, password=self.password)
            except IOError:
                self.warning("Unable to find private key file: %s", self.private_key_file)
            except paramiko.ssh_exception.PasswordRequiredException:
                self.warning("Private key file is encrypted but no password was given")
            except paramiko.ssh_exception.SSHException:
                self.warning("Private key file is invalid")

        client = paramiko.SSHClient()
        if self.add_missing_keys:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.load_system_host_keys()

        exception_message = "No errors occurred"
        try:
            # Try to connect to check status of SSH
            try:
                if not private_key:
                    client.connect(self.host, port=self.port, username=self.username, password=self.password)
                else:
                    # If the private key is not valid and we pass password instead of passphrase it will attempt to
                    # connect using the password and the error will be misleading
                    client.connect(
                        self.host, port=self.port, username=self.username, passphrase=self.password, pkey=private_key
                    )
                self.service_check(self.SSH_SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.base_tags)

            except Exception as e:
                exception_message = str(e)
                status = AgentCheck.CRITICAL
                self.service_check(self.SSH_SERVICE_CHECK_NAME, status, tags=self.base_tags, message=exception_message)
                if self.sftp_check:
                    self.service_check(
                        self.SFTP_SERVICE_CHECK_NAME, status, tags=self.base_tags, message=exception_message
                    )
                raise

            self._collect_metadata(client)

            # Open sftp session on the existing connection to check status of SFTP
            if self.sftp_check:
                try:
                    sftp = client.open_sftp()
                    # Check response time of SFTP
                    start_time = time.time()
                    sftp.listdir('.')
                    status = AgentCheck.OK
                    end_time = time.time()
                    time_taken = end_time - start_time
                    self.gauge('sftp.response_time', time_taken, tags=self.base_tags)

                except Exception as e:
                    exception_message = str(e)
                    status = AgentCheck.CRITICAL

                if status is AgentCheck.OK:
                    exception_message = None

                self.service_check(self.SFTP_SERVICE_CHECK_NAME, status, tags=self.base_tags, message=exception_message)
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
