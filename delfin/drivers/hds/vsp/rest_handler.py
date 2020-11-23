# Copyright 2020 The SODA Authors.
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
import threading

import requests
import six
from oslo_log import log as logging

from delfin import cryptor
from delfin import exception
from delfin.drivers.hds.vsp import consts

LOG = logging.getLogger(__name__)
STATUS_200 = 200
STATUS_201 = 201
STATUS_202 = 202
STATUS_204 = 204
STATUS_401 = 401

class RestHandler(object):
    HDSVSP_SYSTEM_URL = '/ConfigurationManager/v1/objects/storages'
    HDSVSP_LOGOUT_URL = '/ConfigurationManager/v1/objects/sessions/'
    HDSVSP_COMM_URL = '/ConfigurationManager/v1/objects/storages/'

    HDSVSP_AUTH_KEY = 'Authorization'

    def __init__(self, rest_client):
        self.rest_client = rest_client
        self.session_lock = threading.Lock()
        self.hdsvsp_session_id = None
        self.storage_device_id = None
        self.device_model = None
        self.serial_number = None

    def call(self, url, data=None, method=None):
        try:
            res = self.rest_client.do_call(url, data, method,
                                           calltimeout=consts.SOCKET_TIMEOUT)
            if res is not None:
                if (res.status_code == consts.ERROR_SESSION_INVALID_CODE
                        or res.status_code ==
                        consts.ERROR_SESSION_IS_BEING_USED_CODE):
                    LOG.error("Failed to get token=={0}=={1},get token again"
                              .format(res.status_code, res.text))
                    # if method is logout,return immediately
                    if method == 'DELETE' and RestHandler.\
                            HDSVSP_LOGOUT_URL in url:
                        return res
                    self.rest_client.rest_auth_token = None
                    access_session = self.login()
                    if access_session is not None:
                        res = self.rest_client. \
                            do_call(url, data, method,
                                    calltimeout=consts.SOCKET_TIMEOUT)
                    else:
                        LOG.error('Login res is None')
                elif res.status_code == 503:
                    raise exception.InvalidResults(res.text)
            else:
                LOG.error('Rest exec failed,the result in none')

            return res

        except Exception as e:
            err_msg = "Get RestHandler.call failed: %s" % (six.text_type(e))
            LOG.error(err_msg)
            raise exception.InvalidResults(err_msg)

    def get_resinfo_call(self, url, data=None, method=None, resName=None):
        result_json = None
        res = self.call(url, data, method)
        if res is not None:
            if res.status_code == STATUS_200:
                result_json = res.json()
        return result_json

    def login(self):
        try:
            access_session = self.rest_client.rest_auth_token
            if self.rest_client.san_address:
                url = '%s%s/sessions' % \
                      (RestHandler.HDSVSP_COMM_URL,
                       self.storage_device_id)
                data = {}

                with self.session_lock:
                    if self.rest_client.rest_auth_token is not None:
                        return self.rest_client.rest_auth_token
                    if self.rest_client.session is None:
                        self.rest_client.init_http_head()
                    self.rest_client.session.auth = \
                        requests.auth.HTTPBasicAuth(
                            self.rest_client.rest_username,
                            cryptor.decode(self.rest_client.rest_password))
                    res = self.rest_client. \
                        do_call(url, data, 'POST',
                                calltimeout=consts.SOCKET_TIMEOUT)

                    if res is None:
                        LOG.error('Login res is None')
                        raise exception.InvalidResults('Res is None in login')

                    if res.status_code == STATUS_200:
                        result = res.json()
                        self.hdsvsp_session_id = result.get('sessionId')
                        access_session = 'Session %s' % result.get('token')
                        self.rest_client.rest_auth_token = access_session
                        self.rest_client.session.headers[
                            RestHandler.HDSVSP_AUTH_KEY] = access_session
                    else:
                        LOG.error("Login error. URL: %(url)s\n"
                                  "Reason: %(reason)s.",
                                  {"url": url, "reason": res.text})
                        if 'invalid username or password' in res.text:
                            raise exception.InvalidUsernameOrPassword()
                        else:
                            raise exception.BadResponse(res.text)
            else:
                LOG.error('Login Parameter error')

            return access_session
        except Exception as e:
            LOG.error("Login error: %s", six.text_type(e))
            raise e

    def logout(self):
        try:
            url = RestHandler.HDSVSP_LOGOUT_URL
            if self.hdsvsp_session_id is not None:
                url = '%s%s/sessions/%s' % \
                      (RestHandler.HDSVSP_COMM_URL,
                       self.storage_device_id,
                       self.hdsvsp_session_id)
                if self.rest_client.san_address:
                    self.call(url, method='DELETE')
                    self.rest_client.rest_auth_token = None
            else:
                LOG.error('logout error:session id not found')
        except Exception as err:
            LOG.error('logout error:{}'.format(err))
            raise exception.StorageBackendException(
                reason='Failed to Logout from restful')

    def get_device_id(self):
        try:
            if self.rest_client.session is None:
                self.rest_client.init_http_head()
            storage_systems = self.get_system_info()
            if storage_systems is None:
                return
            system_info = storage_systems.get('data')
            for system in system_info:
                if system.get('model') in consts.VSP_MODEL_NOT_USE_SVPIP:
                    if system.get('ctl1Ip') == self.rest_client.rest_host or \
                            system.get('ctl2Ip') == self.rest_client.rest_host:
                        self.storage_device_id = system.get('storageDeviceId')
                        self.device_model = system.get('model')
                        self.serial_number = system.get('serialNumber')
                        break
                elif system.get('svpIp') == self.rest_client.rest_host:
                    self.storage_device_id = system.get('storageDeviceId')
                    self.device_model = system.get('model')
                    self.serial_number = system.get('serialNumber')
                    break
            if self.storage_device_id is None:
                LOG.error("Get device id fail,model or something is wrong")
        except Exception as e:
            LOG.error("Get device id error: %s", six.text_type(e))
            raise e

    def get_specific_storage(self):
        url = '%s%s' % \
              (RestHandler.HDSVSP_COMM_URL, self.storage_device_id)
        result_json = self.get_resinfo_call(url,
                                            method='GET',
                                            resName='Specific_Storage')
        if result_json is None:
            return None
        firmware_version = result_json.get('dkcMicroVersion')

        return firmware_version

    def get_capacity(self):
        url = '%s%s/total-capacities/instance' % \
              (RestHandler.HDSVSP_COMM_URL, self.storage_device_id)
        result_json = self.get_resinfo_call(url,
                                            method='GET',
                                            resName='capacity')
        return result_json

    def get_all_pools(self):
        url = '%s%s/pools' % \
              (RestHandler.HDSVSP_COMM_URL, self.storage_device_id)
        result_json = self.get_resinfo_call(url,
                                            method='GET',
                                            resName='pool')
        return result_json

    def get_all_volumes(self):
        url = '%s%s/ldevs' % \
              (RestHandler.HDSVSP_COMM_URL, self.storage_device_id)
        result_json = self.get_resinfo_call(url,
                                            method='GET',
                                            resName='volume paginated')
        return result_json

    def get_system_info(self):
        result_json = self.get_resinfo_call(RestHandler.HDSVSP_SYSTEM_URL,
                                            method='GET',
                                            resName='ports paginated')

        return result_json