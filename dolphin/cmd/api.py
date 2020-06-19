#!/usr/bin/env python

# Copyright 2020 The SODA Authors.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Starter script for dolphin OS API."""

import eventlet

eventlet.monkey_patch()

import sys

from oslo_config import cfg
from oslo_log import log

from dolphin.common import config  # noqa
from dolphin import service
from dolphin import utils
from dolphin import version
import socket

CONF = cfg.CONF
LOG = log.getLogger(__name__)


def is_port_free(ip, port):
    # Return 0 if operation succeeds, otherwise an error number
    LOG.debug("Trying to connect%s on port %s" % (ip, port))
    with socket.socket() as s:
        return s.connect_ex((ip, port))


def main():
    log.register_options(CONF)
    CONF(sys.argv[1:], project='dolphin',
         version=version.version_string())
    log.setup(CONF, "dolphin")
    utils.monkey_patch()

    if not is_port_free(CONF.my_ip, CONF.dolphin_listen_port):
        LOG.error("Port %s is already in use on ip %s  " % (
            CONF.dolphin_listen_port, CONF.my_ip))
        sys.exit()

    launcher = service.process_launcher()
    api_server = service.WSGIService('dolphin', coordination=True)
    launcher.launch_service(api_server, workers=api_server.workers or 1)
    launcher.wait()


if __name__ == '__main__':
    main()
