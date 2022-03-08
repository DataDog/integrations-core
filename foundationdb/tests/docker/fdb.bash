#! /bin/bash

#
# fdb.bash
#
# This source file is part of the FoundationDB open source project
#
# Copyright 2013-2018 Apple Inc. and the FoundationDB project authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

source /var/fdb/scripts/create_server_environment.bash
create_server_environment
source /var/fdb/.fdbenv

fdbserver --listen_address 0.0.0.0:4600:tls -p $PUBLIC_IP:4600:tls \
          --tls_certificate_file /var/fdb/fdb.pem --tls_key_file /var/fdb/private.key --tls_verify_peers Check.Valid=0 \
          --datadir /var/fdb/data --logdir /var/fdb/logs \
          --locality_zoneid=`hostname` --locality_machineid=`hostname` --class $FDB_PROCESS_CLASS
