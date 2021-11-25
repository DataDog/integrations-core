# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ipaddress
import threading
from collections import defaultdict

import win32api
import win32pdh
import win32wnet

from ....errors import ConfigTypeError


class NetworkResources:
    def __init__(self):
        self.__lock = threading.Lock()
        self.__resources = defaultdict(int)

    def add(self, resource, username, password):
        with self.__lock:
            name = resource.lpRemoteName
            if name not in self.__resources:
                # https://docs.microsoft.com/en-us/windows/win32/api/winnetwk/nf-winnetwk-wnetaddconnection2a
                # http://timgolden.me.uk/pywin32-docs/win32wnet__WNetAddConnection2_meth.html
                win32wnet.WNetAddConnection2(resource, password, username, 0)

            self.__resources[name] += 1

    def remove(self, resource):
        with self.__lock:
            name = resource.lpRemoteName
            if name not in self.__resources:
                return

            self.__resources[name] -= 1
            if self.__resources[name] == 0:
                del self.__resources[name]

                # https://docs.microsoft.com/en-us/windows/win32/api/winnetwk/nf-winnetwk-wnetcancelconnection2a
                # http://timgolden.me.uk/pywin32-docs/win32wnet__WNetCancelConnection2_meth.html
                win32wnet.WNetCancelConnection2(name, 0, 1)


class Connection:
    network_resources = NetworkResources()

    def __init__(self, config):
        machine_name = win32api.GetComputerName().lower()
        self.server = config.get('server', '')
        if not isinstance(self.server, str):
            raise ConfigTypeError('Setting `server` must be a string')
        elif not self.server:
            self.server = machine_name
        else:
            self.server = self.server.lower()

        self.username = config.get('username')
        if self.username is not None and not isinstance(self.username, str):
            raise ConfigTypeError('Setting `username` must be a string')

        self.password = config.get('password')
        if self.password is not None and not isinstance(self.password, str):
            raise ConfigTypeError('Setting `password` must be a string')

        self.network_resource = None
        if self.server != machine_name:
            try:
                ipaddress.IPv6Address(self.server)
            except ipaddress.AddressValueError:
                server = self.server
            else:
                # https://docs.microsoft.com/en-us/windows/win32/api/winnetwk/nf-winnetwk-wnetaddconnection2a#remarks
                server = self.server.replace(':', '-')
                server = f'{server}.ipv6-literal.net'

            # https://docs.microsoft.com/en-us/windows/win32/api/winnetwk/ns-winnetwk-netresourcea
            # http://timgolden.me.uk/pywin32-docs/PyNETRESOURCE.html
            self.network_resource = win32wnet.NETRESOURCE()
            self.network_resource.lpRemoteName = fr'\\{server}'

        self.__query_handle = None

    @property
    def query_handle(self):
        return self.__query_handle

    def connect(self):
        if self.network_resource is not None:
            self.network_resources.add(self.network_resource, self.username, self.password)

        # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhopenquerya
        # http://timgolden.me.uk/pywin32-docs/win32pdh__OpenQuery_meth.html
        self.__query_handle = win32pdh.OpenQuery()

    def disconnect(self):
        # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhclosequery
        # http://timgolden.me.uk/pywin32-docs/win32pdh__CloseQuery_meth.html
        win32pdh.CloseQuery(self.__query_handle)

        if self.network_resource is not None:
            self.network_resources.remove(self.network_resource)

    def reconnect(self):
        self.disconnect()
        self.connect()
