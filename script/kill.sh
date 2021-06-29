#!/usr/bin/env bash

# Copyright 2021 The SODA Authors.
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

KILLALL=$(which killall)
CMD=${KILLALL:-/usr/bin/killall}

if [ -x ${CMD} ]
then
    ${CMD} -qr 'delfin/cmd/api.py'
    ${CMD} -qr 'delfin/cmd/task.py'
    ${CMD} -qr 'delfin/cmd/alert.py'
    ${CMD} -qr 'delfin/exporter/exporter_server.py'
    # more can be added below
fi
exit 0
