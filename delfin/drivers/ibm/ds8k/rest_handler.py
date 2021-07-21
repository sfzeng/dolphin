# Copyright 2021 The SODA Authors.
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

import six
from oslo_log import log as logging

from delfin import cryptor
from delfin import exception
from delfin.drivers.utils.rest_client import RestClient

LOG = logging.getLogger(__name__)


class RestHandler(RestClient):
    REST_TOKEN_URL = '/api/v1/tokens'

    def __init__(self, **kwargs):
        self.session_lock = threading.Lock()
        super(RestHandler, self).__init__(**kwargs)

    def call_with_token(self, url, data, method):
        auth_key = None
        if self.session:
            auth_key = self.session.headers.get('X-Auth-Token', None)
            if auth_key:
                self.session.headers['X-Auth-Token'] \
                    = cryptor.decode(auth_key)
        res = self.do_call(url, data, method)
        if auth_key:
            self.session.headers['X-Auth-Token'] = auth_key
        return res

    def call(self, url, data=None, method=None):
        try:
            res = self.call_with_token(url, data, method)
            if res.status_code == 401:
                LOG.error("Failed to get token,status_code:%s,error_mesg:%s" %
                          (res.status_code, res.text))
                self.login()
                res = self.call_with_token(url, data, method)
            elif res.status_code == 503:
                raise exception.InvalidResults(res.text)
            return res
        except Exception as e:
            LOG.error("Method:%s,url:%s failed: %s" % (method, url,
                                                       six.text_type(e)))
            raise e

    def get_rest_info(self, url, data=None, method='GET'):
        result_json = None
        res = self.call(url, data, method)
        if res.status_code == 200:
            result_json = res.json()
        return result_json

    def login(self):
        try:
            data = {"username": self.rest_username,
                    "password": cryptor.decode(self.rest_password)
                    }
            data = {'request': {'params': data}}
            with self.session_lock:
                if self.session is None:
                    self.init_http_head()
                res = self.call_with_token(
                    RestHandler.REST_TOKEN_URL, data, 'POST')
                if res.status_code == 200:
                    result = res.json()
                    self.session.headers['X-Auth-Token'] = \
                        cryptor.encode(result.get('token').get('token'))
                else:
                    LOG.error("Login error. URL: %(url)s，Reason: %(reason)s.",
                              {"url": RestHandler.REST_TOKEN_URL,
                               "reason": res.text})
                    if 'Authentication has failed' in res.text:
                        raise exception.InvalidUsernameOrPassword()
                    else:
                        raise exception.StorageBackendException(res.text)
        except Exception as e:
            LOG.error("Login error: %s", six.text_type(e))
            raise e

    def logout(self):
        try:
            if self.san_address:
                self.call(RestHandler.REST_TOKEN_URL, method='DELETE')
            if self.session:
                self.session.close()
        except Exception as e:
            err_msg = "Logout error: %s" % (six.text_type(e))
            LOG.error(err_msg)
            raise e

    def get_storage(self):
        result_json = self.get_rest_info('/api/v1/systems')
        return result_json

    def get_all_pools(self):
        result_json = self.get_rest_info('/api/v1/pools')
        return result_json

    def get_pool_volumes(self, pool_id):
        url = '/api/v1/pools/%s/volumes' % pool_id
        result_json = self.get_rest_info(url)
        return result_json

    def get_all_alerts(self):
        result_json = \
            self.get_rest_info('/api/v1/events?severity=warning,error')
        return result_json
