# Copyright 2020 The SODA Authors.
# Copyright (c) 2020 Dell Inc. or its subsidiaries.
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

import json
import sys

import requests
import requests.auth
import requests.exceptions as r_exc
import six
import urllib3
from oslo_log import log as logging

from delfin import cryptor
from delfin import exception
from delfin import ssl_utils
from delfin.common import alert_util
from delfin.drivers.dell_emc.vmax import perf_utils, constants
from delfin.i18n import _

LOG = logging.getLogger(__name__)
SLOPROVISIONING = 'sloprovisioning'
U4V_VERSION = '92'
UCODE_5978 = '5978'
# HTTP constants
GET = 'GET'
POST = 'POST'
PUT = 'PUT'
DELETE = 'DELETE'
STATUS_200 = 200
STATUS_201 = 201
STATUS_202 = 202
STATUS_204 = 204
STATUS_401 = 401

# Default expiration time(in sec) for vmax connect request
VERSION_GET_TIME_OUT = 10


class VMaxRest(object):
    """Rest class based on Unisphere for VMax Rest API."""

    def __init__(self):
        self.session = None
        self.base_uri = None
        self.user = None
        self.passwd = None
        self.verify = None
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def set_rest_credentials(self, array_info):
        """Given the array record set the rest server credentials.
        :param array_info: record
        """
        ip = array_info['host']
        port = array_info['port']
        self.user = array_info['username']
        self.passwd = array_info['password']
        ip_port = "%(ip)s:%(port)d" % {'ip': ip, 'port': port}
        self.base_uri = ("https://%(ip_port)s/univmax/restapi" % {
            'ip_port': ip_port})

    def establish_rest_session(self):
        """Establish the rest session.
        :returns: requests.session() -- session, the rest session
        """
        LOG.info("Establishing REST session with %(base_uri)s",
                 {'base_uri': self.base_uri})
        if self.session:
            self.session.close()
        session = requests.session()
        session.headers = {'content-type': 'application/json',
                           'accept': 'application/json',
                           'Application-Type': 'delfin'}
        session.auth = requests.auth.HTTPBasicAuth(
            self.user, cryptor.decode(self.passwd))

        if not self.verify:
            session.verify = False
        else:
            LOG.debug("Enable certificate verification, ca_path: {0}".format(
                self.verify))
            session.verify = self.verify
        session.mount("https://", ssl_utils.get_host_name_ignore_adapter())

        self.session = session
        return session

    def request(self, target_uri, method, params=None, request_object=None,
                timeout=None):
        """Sends a request (GET, POST, PUT, DELETE) to the target api.
        :param target_uri: target uri (string)
        :param method: The method (GET, POST, PUT, or DELETE)
        :param params: Additional URL parameters
        :param request_object: request payload (dict)
        :param timeout: expiration timeout(in sec)
        :returns: server response object (dict)
        :raises: StorageBackendException, Timeout, ConnectionError,
                 HTTPError, SSLError
        """

        url, message, status_code, response = None, None, None, None
        if not self.session:
            self.establish_rest_session()

        try:
            url = ("%(self.base_uri)s%(target_uri)s" % {
                'self.base_uri': self.base_uri,
                'target_uri': target_uri})

            if request_object:
                response = self.session.request(
                    method=method, url=url,
                    data=json.dumps(request_object, sort_keys=True,
                                    indent=4), timeout=timeout)
            elif params:
                response = self.session.request(
                    method=method, url=url, params=params, timeout=timeout)
            else:
                response = self.session.request(
                    method=method, url=url, timeout=timeout)

            status_code = response.status_code

            try:
                message = response.json()
            except ValueError:
                LOG.debug("No response received from API. Status code "
                          "received is: %(status_code)s", {
                              'status_code': status_code})
                message = None

            LOG.debug("%(method)s request to %(url)s has returned with "
                      "a status code of: %(status_code)s.", {
                          'method': method, 'url': url,
                          'status_code': status_code})

        except r_exc.SSLError as e:
            msg = _("The connection to %(base_uri)s has encountered an "
                    "SSL error. Please check your SSL config or supplied "
                    "SSL cert in Delfin configuration. SSL Exception "
                    "message: %(e)s") % {'base_uri': self.base_uri, 'e': e}
            LOG.error(msg)
            err_str = six.text_type(e)
            if 'certificate verify failed' in err_str:
                raise exception.SSLCertificateFailed()
            else:
                raise exception.SSLHandshakeFailed()

        except (r_exc.Timeout, r_exc.ConnectionError,
                r_exc.HTTPError) as e:
            exc_class, __, __ = sys.exc_info()
            msg = _("The %(method)s to Unisphere server %(base)s has "
                    "experienced a %(error)s error. Please check your "
                    "Unisphere server connection/availability. "
                    "Exception message: %(exc_msg)s")
            raise exc_class(msg % {'method': method,
                                   'base': self.base_uri,
                                   'error': e.__class__.__name__,
                                   'exc_msg': e})

        except Exception as e:
            msg = _("The %(method)s request to URL %(url)s failed with "
                    "exception %(e)s")
            LOG.error(msg, {'method': method, 'url': url,
                            'e': six.text_type(e)})
            raise exception.StorageBackendException(
                message=(msg, {'method': method, 'url': url,
                               'e': six.text_type(e)}))

        return status_code, message

    @staticmethod
    def check_status_code_success(operation, status_code, message):
        """Check if a status code indicates success.
        :param operation: the operation
        :param status_code: the status code
        :param message: the server response
        :raises: StorageBackendException
        """
        if status_code not in [STATUS_200, STATUS_201,
                               STATUS_202, STATUS_204]:
            exception_message = (
                _("Error %(operation)s. The status code received is %(sc)s "
                  "and the message is %(message)s.") % {
                    'operation': operation, 'sc': status_code,
                    'message': message})
            raise exception.StorageBackendException(
                message=exception_message)

    def build_uri(self, *args, **kwargs):
        """Build the target url.
        :param args: input args, see _build_uri_legacy_args() for input
                     breakdown
        :param kwargs: input keyword args, see _build_uri_kwargs() for input
                       breakdown
        :return: target uri -- str
        """
        if args:
            target_uri = self._build_uri_legacy_args(*args, **kwargs)
        else:
            target_uri = self._build_uri_kwargs(**kwargs)

        return target_uri

    @staticmethod
    def _build_uri_legacy_args(*args, **kwargs):
        """Build the target URI using legacy args & kwargs.
        Expected format:
            arg[0]: the array serial number: the array serial number -- str
            arg[1]: the resource category e.g. 'sloprovisioning' -- str
            arg[2]: the resource type e.g. 'maskingview' -- str
            kwarg resource_name: the name of a specific resource -- str
            kwarg private: if endpoint is private -- bool
            kwarg version: U4V REST endpoint version -- int/str
            kwarg no_version: if endpoint should be versionless -- bool
        :param args: input args -- see above
        :param kwargs: input keyword args -- see above
        :return: target URI -- str
        """
        # Extract args following legacy _build_uri() format
        array_id, category, resource_type = args[0], args[1], args[2]
        # Extract keyword args following legacy _build_uri() format
        resource_name = kwargs.get('resource_name')
        private = kwargs.get('private')
        version = kwargs.get('version', U4V_VERSION)
        if kwargs.get('no_version'):
            version = None

        # Build URI
        target_uri = ''
        if private:
            target_uri += '/private'
        if version:
            target_uri += '/%(version)s' % {'version': version}
        target_uri += (
            '/{cat}/symmetrix/{array_id}/{res_type}'.format(
                cat=category, array_id=array_id, res_type=resource_type))
        if resource_name:
            target_uri += '/{resource_name}'.format(
                resource_name=kwargs.get('resource_name'))

        return target_uri

    @staticmethod
    def _build_uri_kwargs(**kwargs):
        """Build the target URI using kwargs.
        Expected kwargs:
            private: if endpoint is private (optional) -- bool
            version: U4P REST endpoint version (optional) -- int/None
            no_version: if endpoint should be versionless (optional) -- bool
            category: U4P REST category eg. 'common', 'replication'-- str
            resource_level: U4P REST resource level eg. 'symmetrix'
                            (optional) -- str
            resource_level_id: U4P REST resource level id (optional) -- str
            resource_type: U4P REST resource type eg. 'rdf_director', 'host'
                           (optional) -- str
            resource_type_id: U4P REST resource type id (optional) -- str
            resource: U4P REST resource eg. 'port' (optional) -- str
            resource_id: U4P REST resource id (optional) -- str
            object_type: U4P REST resource eg. 'rdf_group' (optional) -- str
            object_type_id: U4P REST resource id (optional) -- str
        :param kwargs: input keyword args -- see above
        :return: target URI -- str
        """
        version = kwargs.get('version', U4V_VERSION)
        if kwargs.get('no_version'):
            version = None

        target_uri = ''

        if kwargs.get('private'):
            target_uri += '/private'

        if version:
            target_uri += '/%(ver)s' % {'ver': version}

        target_uri += '/%(cat)s' % {'cat': kwargs.get('category')}

        if kwargs.get('resource_level'):
            target_uri += '/%(res_level)s' % {
                'res_level': kwargs.get('resource_level')}

        if kwargs.get('resource_level_id'):
            target_uri += '/%(res_level_id)s' % {
                'res_level_id': kwargs.get('resource_level_id')}

        if kwargs.get('resource_type'):
            target_uri += '/%(res_type)s' % {
                'res_type': kwargs.get('resource_type')}
            if kwargs.get('resource_type_id'):
                target_uri += '/%(res_type_id)s' % {
                    'res_type_id': kwargs.get('resource_type_id')}

        if kwargs.get('resource'):
            target_uri += '/%(res)s' % {
                'res': kwargs.get('resource')}
            if kwargs.get('resource_id'):
                target_uri += '/%(res_id)s' % {
                    'res_id': kwargs.get('resource_id')}

        if kwargs.get('object_type'):
            target_uri += '/%(object_type)s' % {
                'object_type': kwargs.get('object_type')}
            if kwargs.get('object_type_id'):
                target_uri += '/%(object_type_id)s' % {
                    'object_type_id': kwargs.get('object_type_id')}

        return target_uri

    def get_request(self, target_uri, resource_type, params=None):
        """Send a GET request to the array.
        :param target_uri: the target uri
        :param resource_type: the resource type, e.g. maskingview
        :param params: optional dict of filter params
        :returns: resource_object -- dict or None
        """
        resource_object = None
        sc, message = self.request(target_uri, GET, params=params)
        operation = 'get %(res)s' % {'res': resource_type}
        try:
            self.check_status_code_success(operation, sc, message)
        except Exception as e:
            LOG.debug("Get resource failed with %(e)s",
                      {'e': e})
        if sc == STATUS_200:
            resource_object = message
            resource_object = self.list_pagination(resource_object)
        return resource_object

    def get_alert_request(self, target_uri):
        """Send a GET request to the array.
        :param target_uri: the target uri
        :returns: resource_object -- dict or None
        """
        sc, message = self.request(target_uri, GET, params=None)
        if sc != STATUS_200:
            raise exception.StorageListAlertFailed(message)
        resource_object = message
        resource_object = self.list_pagination(resource_object)
        return resource_object

    def get_resource(self, array, category, resource_type,
                     resource_name=None, params=None, private=False,
                     version=U4V_VERSION):
        """Get resource details from array.
        :param array: the array serial number
        :param category: the resource category e.g. sloprovisioning
        :param resource_type: the resource type e.g. maskingview
        :param resource_name: the name of a specific resource
        :param params: query parameters
        :param private: empty string or '/private' if private url
        :param version: None or specific version number if required
        :returns: resource object -- dict or None
        """
        target_uri = self.build_uri(
            array, category, resource_type, resource_name=resource_name,
            private=private, version=version)
        return self.get_request(target_uri, resource_type, params)

    def get_array_detail(self, version=U4V_VERSION, array=''):
        """Get an array from its serial number.
        :param array: the array serial number
        :param version: the unisphere version
        :returns: array_details -- dict or None
        """
        target_uri = '/%s/system/symmetrix/%s' % (version, array)
        array_details = self.get_request(target_uri, 'system')
        if not array_details:
            LOG.error("Cannot connect to array %(array)s.",
                      {'array': array})
        return array_details

    def get_uni_version(self):
        """Get the unisphere version from the server.
        :returns: version and major_version(e.g. ("V8.4.0.16", "84"))
        """
        version, major_version = None, None
        response = self.get_unisphere_version()
        if response and response.get('version'):
            version = response['version']
            version_list = version.split('.')
            major_version = version_list[0][1] + version_list[1]
        return version, major_version

    def get_unisphere_version(self):
        """Get the unisphere version from the server.
        :returns: version dict
        """
        post_90_endpoint = '/version'
        pre_91_endpoint = '/system/version'

        status_code, version_dict = self.request(
            post_90_endpoint, GET, timeout=VERSION_GET_TIME_OUT)
        if status_code is not STATUS_200:
            status_code, version_dict = self.request(
                pre_91_endpoint, GET, timeout=VERSION_GET_TIME_OUT)

        if status_code == STATUS_401:
            raise exception.InvalidUsernameOrPassword()

        if not version_dict:
            LOG.error("Unisphere version info not found.")
        return version_dict

    def get_srp_by_name(self, array, version, srp=None):
        """Returns the details of a storage pool.
        :param array: the array serial number
        :param version: the unisphere version
        :param srp: the storage resource pool name
        :returns: SRP_details -- dict or None
        """
        LOG.debug("storagePoolName: %(srp)s, array: %(array)s.",
                  {'srp': srp, 'array': array})
        srp_details = self.get_resource(array, SLOPROVISIONING, 'srp',
                                        resource_name=srp, version=version,
                                        params=None)
        return srp_details

    def get_vmax_array_details(self, version=U4V_VERSION, array=''):
        """Get the VMax array properties.
        :param version: the unisphere version
        :param array: the array serial number
        :returns: the VMax model
        """
        system_info = self.get_array_detail(version, array)
        vmax_version = system_info.get('model')
        vmax_ucode = system_info.get('ucode')
        vmax_display_name = system_info.get('display_name')
        array_details = {"model": vmax_version,
                         "ucode": vmax_ucode,
                         "display_name": vmax_display_name}
        return array_details

    def get_array_model_info(self, version=U4V_VERSION, array=''):
        """Get the VMax model.
        :param version: the unisphere version
        :param array: the array serial number
        :returns: the VMax model
        """
        is_next_gen = False
        system_info = self.get_array_detail(version, array)
        array_model = system_info.get('model', None)
        ucode_version = system_info['ucode'].split('.')[0]
        if ucode_version >= UCODE_5978:
            is_next_gen = True
        return array_model, is_next_gen

    def get_storage_group(self, array, version, storage_group_name):
        """Given a name, return storage group details.
        :param version: the unisphere version
        :param array: the array serial number
        :param storage_group_name: the name of the storage group
        :returns: storage group dict or None
        """
        return self.get_resource(
            array, SLOPROVISIONING, 'storagegroup',
            version=version,
            resource_name=storage_group_name)

    def get_system_capacity(self, array, version):
        target_uri = '/%s/sloprovisioning/symmetrix/%s' % (version, array)
        capacity_details = self.get_request(target_uri, None)
        if not capacity_details:
            LOG.error("Cannot connect to array %(array)s.",
                      {'array': array})
        return capacity_details

    def get_default_srps(self, array, version=U4V_VERSION):
        """Get the VMax array default SRPs.
        :param version: the unisphere version
        :param array: the array serial number
        :returns: dictionary default SRPs
        """
        symmetrix_info = self.get_system_capacity(array, version)
        default_fba_srp = symmetrix_info.get('default_fba_srp', None)
        default_ckd_srp = symmetrix_info.get('default_ckd_srp', None)
        default_srps = {"FBA": default_fba_srp,
                        "CKD": default_ckd_srp}
        return default_srps

    def get_volume(self, array, version, device_id):
        """Get a VMax volume from array.
        :param array: the array serial number
        :param device_id: the volume device id
        :returns: volume dict
        :raises: StorageBackendException
        """
        volume_dict = self.get_resource(
            array, SLOPROVISIONING, 'volume', resource_name=device_id,
            version=version)
        if not volume_dict:
            exception_message = (_("Volume %(deviceID)s not found.")
                                 % {'deviceID': device_id})
            LOG.error(exception_message)
            raise exception.StorageBackendException(
                message=exception_message)
        return volume_dict

    def get_volume_list(self, array, version, params):
        """Get a filtered list of VMax volumes from array.
        Filter parameters are required as the unfiltered volume list could be
        very large and could affect performance if called often.
        :param array: the array serial number
        :param version: the unisphere version
        :param params: filter parameters
        :returns: device_ids -- list
        """
        device_ids = []
        volume_dict_list = self.get_resource(
            array, SLOPROVISIONING, 'volume', version=version, params=params)
        try:
            for vol_dict in volume_dict_list:
                device_id = vol_dict['volumeId']
                device_ids.append(device_id)
        except (KeyError, TypeError):
            pass
        return device_ids

    def post_request(self, target_uri, payload):
        """Generate  a POST request.
        :param target_uri: the uri to query from unipshere REST API
        :param payload: the payload
        :returns: status_code -- int, message -- string, server response
        """

        status_code, message = self.request(target_uri, POST,
                                            request_object=payload)
        operation = 'POST request for URL' % {target_uri}
        self.check_status_code_success(
            operation, status_code, message)
        return status_code, message

    def get_array_performance_metrics(self, array, start_time, end_time):
        """Get a array performance metrics from VMAX unipshere REST API.
        :param array: the array serial number
        :param start_time: start time for collection
        :param end_time: end time for collection
        :returns: message -- response from unipshere REST API
         """

        target_uri = constants.VMAX_REST_TARGET_URI_ARRAY_PERF
        payload = perf_utils.generate_performance_payload(
            array, start_time, end_time, constants.ARRAY_METRICS)

        status_code, message = self.post_request(target_uri, payload)
        # Expected 200 when POST request has metrics in response body
        if status_code != STATUS_200:
            raise exception.StoragePerformanceCollectionFailed(message)
        return message

    def get_pool_performance_metrics(self, pool_id, array, start_time, end_time):
        """Get a array performance metrics from VMAX unipshere REST API.
        :param array: the array serial number
        :param start_time: start time for collection
        :param end_time: end time for collection
        :returns: message -- response from unipshere REST API
         """

        target_uri = constants.VMAX_REST_TARGET_URI_ARRAY_PERF
        payload = perf_utils.generate_performance_payload(
            array, start_time, end_time, constants.ARRAY_METRICS)
        payload['srpId'] = pool_id
        status_code, message = self.post_request(target_uri, payload)
        # Expected 200 when POST request has metrics in response body
        if status_code != STATUS_200:
            raise exception.StoragePoolPerformanceCollectionFailed(message)
        return message

    def list_pagination(self, list_info):
        """Process lists under or over the maxPageSize
        :param list_info: the object list information
        :returns: the result list
        """
        result_list = []
        try:
            result_list = list_info['resultList']['result']
            iterator_id = list_info['id']
            list_count = list_info['count']
            max_page_size = list_info['maxPageSize']
            start_position = list_info['resultList']['from']
            end_position = list_info['resultList']['to']
        except (KeyError, TypeError):
            return list_info
        if list_count > max_page_size:
            LOG.info("More entries exist in the result list, retrieving "
                     "remainder of results from iterator.")

            start_position = end_position + 1
            if list_count < (end_position + max_page_size):
                end_position = list_count
            else:
                end_position += max_page_size
            iterator_response = self.get_iterator_page_list(
                iterator_id, list_count, start_position, end_position,
                max_page_size)

            result_list += iterator_response
        return result_list

    def get_iterator_page_list(self, iterator_id, result_count, start_position,
                               end_position, max_page_size):
        """Iterate through response if more than one page available.
        :param iterator_id: the iterator ID
        :param result_count: the amount of results in the iterator
        :param start_position: position to begin iterator from
        :param end_position: position to stop iterator
        :param max_page_size: the max page size
        :returns: list -- merged results from multiple pages
        """
        iterator_result = []
        has_more_entries = True

        while has_more_entries:
            if start_position <= result_count <= end_position:
                end_position = result_count
                has_more_entries = False

            params = {'to': end_position, 'from': start_position}
            target_uri = ('/common/Iterator/%(iterator_id)s/page' % {
                'iterator_id': iterator_id})
            iterator_response = self.get_request(target_uri, 'iterator',
                                                 params)
            try:
                iterator_result += iterator_response['result']
                start_position += max_page_size
                end_position += max_page_size
            except (KeyError, TypeError):
                pass

        return iterator_result

    def get_alerts(self, query_para, array, version):
        """Get all alerts with given version and arrayid
        :param query_para: Contains optional begin and end time
        :param array: the array serial number
        :param version: the unisphere version
        :returns: alert_list -- dict or None
        """
        target_uri = '/%s/system/symmetrix/%s/alert?acknowledged=false' \
                     % (version, array)

        # First get list of all alert ids
        alert_id_list = self.get_alert_request(target_uri)
        if not alert_id_list:
            # No current alert ids found
            return []

        # For each alert id, get details of alert
        # Above list is prefixed with 'alertId'
        alert_id_list = alert_id_list['alertId']
        alert_list = []
        for alert_id in alert_id_list:
            target_uri = '/%s/system/symmetrix/%s/alert/%s' \
                         % (version, array, alert_id)
            alert = self.get_alert_request(target_uri)
            if alert is not None and alert_util.is_alert_in_time_range(
                    query_para, alert['created_date_milliseconds']):
                alert_list.append(alert)

        return alert_list

    def clear_alert(self, sequence_number, array, version):
        """Clears alert for given sequence number
        :param sequence_number: unique id of the alert
        :param array: the array serial number
        :param version: the unisphere version
        :returns: result -- success/failure
        """
        target_uri = '/%s/system/symmetrix/%s/alert/%s' \
                     % (version, array, sequence_number)

        status, message = self.request(target_uri, DELETE, params=None)
        if status != STATUS_204:
            raise exception.StorageClearAlertFailed(message)
        return status
