# Copyright 2020 The SODA Authors.
# Copyright (c) 2016 Huawei Technologies Co., Ltd.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
from oslo_log import log as logging
from delfin import exception

LOG = logging.getLogger(__name__)


class NaviClient(object):
    SOCKET_TIMEOUT = 5

    def __init__(self):
        pass

    def exec(self, command_str):
        result = None
        try:
            re = os.popen(command_str)
            if re:
                result = re.read()
                if 'Caller not privileged' in result:
                    raise exception.NaviCallerNotPrivileged
                elif 'Security file not found' in result:
                    raise exception.NaviCallerNotPrivileged
                elif 'error occurred while trying to connect' in result:
                    raise exception.NaviCliConnectTimeout(result)
                elif 'connection refused' in result:
                    raise exception.NaviCliConnectTimeout(result)
        except Exception as e:
            raise e
        return result