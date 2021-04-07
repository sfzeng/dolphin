# Copyright 2020 The SODA Authors.
# Copyright 2010 OpenStack LLC.
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

import routes
import webob.dec
import webob.request
from oslo_service import wsgi

from delfin import context
from delfin import exception
from delfin.api.common import wsgi as os_wsgi
from delfin.common import config, constants  # noqa
from delfin.db.sqlalchemy import models


@webob.dec.wsgify
def fake_wsgi(self, req):
    return self.application


class TestRouter(wsgi.Router):
    def __init__(self, controller):
        mapper = routes.Mapper()
        mapper.resource("test", "tests",
                        controller=os_wsgi.Resource(controller))
        super(TestRouter, self).__init__(mapper)


class HTTPRequest(os_wsgi.Request):

    @classmethod
    def blank(cls, *args, **kwargs):
        if not kwargs.get('base_url'):
            kwargs['base_url'] = 'http://localhost/v1'
        use_admin_context = kwargs.pop('use_admin_context', False)
        out = os_wsgi.Request.blank(*args, **kwargs)
        out.environ['delfin.context'] = context.RequestContext(
            is_admin=use_admin_context)
        return out


def fake_storages_get_all(context, marker=None, limit=None, sort_keys=None,
                          sort_dirs=None, filters=None, offset=None):
    return [
        {
            "id": "12c2d52f-01bc-41f5-b73f-7abf6f38a2a6",
            "created_at": "2020-06-09T08:59:48.710890",
            "free_capacity": 1045449,
            "updated_at": "2020-06-09T08:59:48.769470",
            "name": "fake_driver",
            "location": "HK",
            "firmware_version": "1.0.0",
            "vendor": "fake_vendor",
            "status": "normal",
            "sync_status": constants.SyncStatus.SYNCED,
            "model": "fake_model",
            "description": "it is a fake driver.",
            "serial_number": "2102453JPN12KA0000113",
            "used_capacity": 3126,
            "total_capacity": 1048576,
            'raw_capacity': 1610612736000,
            'subscribed_capacity': 219902325555200
        },
        {
            "id": "277a1d8f-a36e-423e-bdd9-db154f32c289",
            "created_at": "2020-06-09T08:58:23.008821",
            "free_capacity": 1045449,
            "updated_at": "2020-06-09T08:58:23.033601",
            "name": "fake_driver",
            "location": "HK",
            "firmware_version": "1.0.0",
            "vendor": "fake_vendor",
            "status": "normal",
            "sync_status": constants.SyncStatus.SYNCED,
            "model": "fake_model",
            "description": "it is a fake driver.",
            "serial_number": "2102453JPN12KA0000112",
            "used_capacity": 3126,
            "total_capacity": 1048576,
            'raw_capacity': 1610612736000,
            'subscribed_capacity': 219902325555200

        }
    ]


def fake_storages_get_all_with_filter(
        context, marker=None, limit=None,
        sort_keys=None, sort_dirs=None, filters=None, offset=None):
    return [
        {
            "id": "12c2d52f-01bc-41f5-b73f-7abf6f38a2a6",
            "created_at": "2020-06-09T08:59:48.710890",
            "free_capacity": 1045449,
            "updated_at": "2020-06-09T08:59:48.769470",
            "name": "fake_driver",
            "location": "HK",
            "firmware_version": "1.0.0",
            "vendor": "fake_vendor",
            "status": "normal",
            "sync_status": constants.SyncStatus.SYNCED,
            "model": "fake_model",
            "description": "it is a fake driver.",
            "serial_number": "2102453JPN12KA0000113",
            "used_capacity": 3126,
            "total_capacity": 1048576,
            'raw_capacity': 1610612736000,
            'subscribed_capacity': 219902325555200
        }
    ]


def fake_storages_show(context, storage_id):
    return {
        "id": "12c2d52f-01bc-41f5-b73f-7abf6f38a2a6",
        "created_at": "2020-06-09T08:59:48.710890",
        "free_capacity": 1045449,
        "updated_at": "2020-06-09T08:59:48.769470",
        "name": "fake_driver",
        "location": "HK",
        "firmware_version": "1.0.0",
        "vendor": "fake_vendor",
        "status": "normal",
        "sync_status": constants.SyncStatus.SYNCED,
        "model": "fake_model",
        "description": "it is a fake driver.",
        "serial_number": "2102453JPN12KA0000113",
        "used_capacity": 3126,
        "total_capacity": 1048576,
        'raw_capacity': 1610612736000,
        'subscribed_capacity': 219902325555200
    }


def fake_access_info_get_all(context, marker=None, limit=None, sort_keys=None,
                             sort_dirs=None, filters=None, offset=None):
    return [
        {
            'created_at': "2020-06-09T08:59:48.710890",
            'storage_id': '5f5c806d-2e65-473c-b612-345ef43f0642',
            'model': 'fake_driver',
            'vendor': 'fake_storage',
            'rest': {
                'host': '10.0.0.76',
                'port': 1234,
                'username': 'admin',
                'password': b'YWJjZA=='
            },
            'extra_attributes': {'array_id': '0001234567891'},
            'updated_at': None
        }
    ]


def fake_sync(self, req, id):
    pass


def fake_v3_alert_source_config():
    return {'host': '127.0.0.1',
            'version': 'snmpv3',
            'security_level': 'authPriv',
            'engine_id': '800000d30300000e112245',
            'username': 'test1',
            'auth_key': 'abcd123456',
            'auth_protocol': 'HMACMD5',
            'privacy_key': 'abcd123456',
            'privacy_protocol': 'DES',
            'context_name': 'NA',
            'retry_num': 2,
            'expiration': 2,
            'port': 161
            }


def fake_v2_alert_source_config():
    return {'host': '127.0.0.1',
            'version': 'snmpv2c',
            'community_string': 'public',
            'context_name': 'NA',
            'retry_num': 2,
            'expiration': 2,
            'port': 161
            }


def fake_v3_alert_source():
    alert_source = models.AlertSource()
    alert_source.host = '127.0.0.1'
    alert_source.storage_id = 'abcd-1234-5678'
    alert_source.version = 'snmpv3'
    alert_source.engine_id = '800000d30300000e112245'
    alert_source.username = 'test1'
    alert_source.auth_key = 'YWJjZDEyMzQ1Njc='
    alert_source.auth_protocol = 'HMACMD5'
    alert_source.privacy_key = 'YWJjZDEyMzQ1Njc='
    alert_source.privacy_protocol = 'DES'
    alert_source.port = 161
    alert_source.context_name = ""
    alert_source.retry_num = 1
    alert_source.expiration = 1
    alert_source.created_at = '2020-06-15T09:50:31.698956'
    alert_source.updated_at = '2020-06-15T09:50:31.698956'
    return alert_source


def fake_v3_alert_source_noauth_nopriv():
    alert_source = models.AlertSource()
    alert_source.host = '127.0.0.1'
    alert_source.storage_id = 'abcd-1234-5678'
    alert_source.version = 'snmpv3'
    alert_source.security_level = 'noAuthnoPriv'
    alert_source.engine_id = '800000d30300000e112245'
    alert_source.username = 'test1'
    alert_source.port = 161
    alert_source.context_name = ""
    alert_source.retry_num = 1
    alert_source.expiration = 1
    alert_source.created_at = '2020-06-15T09:50:31.698956'
    alert_source.updated_at = '2020-06-15T09:50:31.698956'
    return alert_source


def fake_v3_alert_source_auth_nopriv():
    alert_source = models.AlertSource()
    alert_source.host = '127.0.0.1'
    alert_source.storage_id = 'abcd-1234-5678'
    alert_source.version = 'snmpv3'
    alert_source.security_level = 'authNoPriv'
    alert_source.auth_protocol = 'HMACMD5'
    alert_source.engine_id = '800000d30300000e112245'
    alert_source.username = 'test1'
    alert_source.port = 161
    alert_source.context_name = ""
    alert_source.retry_num = 1
    alert_source.expiration = 1
    alert_source.created_at = '2020-06-15T09:50:31.698956'
    alert_source.updated_at = '2020-06-15T09:50:31.698956'
    return alert_source


def fake_v2_alert_source():
    alert_source = models.AlertSource()
    alert_source.host = '127.0.0.1'
    alert_source.storage_id = 'abcd-1234-5678'
    alert_source.version = 'snmpv2c'
    alert_source.community_string = 'public'
    alert_source.port = 161
    alert_source.context_name = ""
    alert_source.retry_num = 1
    alert_source.expiration = 1
    alert_source.created_at = '2020-06-15T09:50:31.698956'
    alert_source.updated_at = '2020-06-15T09:50:31.698956'
    return alert_source


def alert_source_get_exception(ctx, storage_id):
    raise exception.AlertSourceNotFound('abcd-1234-5678')


def fake_access_info_show(context, storage_id):
    access_info = models.AccessInfo()

    access_info.updated_at = '2020-06-15T09:50:31.698956'
    access_info.storage_id = '865ffd4d-f1f7-47de-abc3-5541ef44d0c1'
    access_info.created_at = '2020-06-15T09:50:31.698956'
    access_info.vendor = 'fake_storage'
    access_info.model = 'fake_driver'
    access_info.rest = {
        'host': '10.0.0.0',
        'username': 'admin',
        'password': 'YWJjZA==',
        'port': 1234
    }
    access_info.extra_attributes = {'array_id': '0001234567897'}

    return access_info


def fake_update_access_info(self, context, access_info):
    access_info = models.AccessInfo()

    access_info.updated_at = '2020-06-15T09:50:31.698956'
    access_info.storage_id = '865ffd4d-f1f7-47de-abc3-5541ef44d0c1'
    access_info.created_at = '2020-06-15T09:50:31.698956'
    access_info.vendor = 'fake_storage'
    access_info.model = 'fake_driver'
    access_info.rest = {
        'host': '10.0.0.0',
        'username': 'admin_modified',
        'password': 'YWJjZA==',
        'port': 1234
    }
    access_info.extra_attributes = {'array_id': '0001234567897'}

    return access_info


def fake_volume_get_all(context, marker=None,
                        limit=None, sort_keys=None,
                        sort_dirs=None, filters=None, offset=None):
    return [
        {
            "created_at": "2020-06-10T07:17:31.157079",
            "updated_at": "2020-06-10T07:17:31.157079",
            "id": "d7fe425b-fddc-4ba4-accb-4343c142dc47",
            "name": "004DF",
            "storage_id": "5f5c806d-2e65-473c-b612-345ef43f0642",
            "native_storage_pool_id": "SRP_1",
            "description": "fake_storage 'thin device' volume",
            "status": "available",
            "native_volume_id": "004DF",
            "wwn": "60000970000297801855533030344446",
            "type": 'thin',
            "total_capacity": 1075838976,
            "used_capacity": 0,
            "free_capacity": 1075838976,
            "compressed": True,
            "deduplicated": False
        },
        {
            "created_at": "2020-06-10T07:17:31.157079",
            "updated_at": "2020-06-10T07:17:31.157079",
            "id": "dad84a1f-db8d-49ab-af40-048fc3544c12",
            "name": "004E0",
            "storage_id": "5f5c806d-2e65-473c-b612-345ef43f0642",
            "native_storage_pool_id": "SRP_1",
            "description": "fake_storage 'thin device' volume",
            "status": "available",
            "native_volume_id": "004E0",
            "wwn": "60000970000297801855533030344530",
            "type": 'thin',
            "total_capacity": 1075838976,
            "used_capacity": 0,
            "free_capacity": 1075838976,
            "compressed": True,
            "deduplicated": False
        }
    ]


def fake_volume_show(context, volume_id):
    return {
        "created_at": "2020-06-10T07:17:31.157079",
        "updated_at": "2020-06-10T07:17:31.157079",
        "id": "d7fe425b-fddc-4ba4-accb-4343c142dc47",
        "name": "004DF",
        "storage_id": "5f5c806d-2e65-473c-b612-345ef43f0642",
        "native_storage_pool_id": "SRP_1",
        "description": "fake_storage 'thin device' volume",
        "status": "available",
        "native_volume_id": "004DF",
        "wwn": "60000970000297801855533030344446",
        "type": 'thin',
        "total_capacity": 1075838976,
        "used_capacity": 0,
        "free_capacity": 1075838976,
        "compressed": True,
        "deduplicated": False
    }


def fake_storage_pool_get_all(context, marker=None,
                              limit=None, sort_keys=None,
                              sort_dirs=None, filters=None, offset=None):
    return [
        {
            "created_at": "2020-06-10T07:17:08.707356",
            "updated_at": "2020-06-10T07:17:08.707356",
            "id": "14155a1f-f053-4ccb-a846-ed67e4387428",
            "name": "SRP_1",
            "storage_id": '12c2d52f-01bc-41f5-b73f-7abf6f38a2a6',
            "native_storage_pool_id": "SRP_1",
            "description": "fake storage Pool",
            "status": "normal",
            "storage_type": "block",
            "total_capacity": 26300318136401,
            "used_capacity": 19054536509358,
            "free_capacity": 7245781627043,
            'subscribed_capacity': 219902325555200
        }
    ]


def fake_storage_pool_show(context, storage_pool_id):
    return {
        "created_at": "2020-06-10T07:17:08.707356",
        "updated_at": "2020-06-10T07:17:08.707356",
        "id": "14155a1f-f053-4ccb-a846-ed67e4387428",
        "name": "SRP_1",
        "storage_id": '12c2d52f-01bc-41f5-b73f-7abf6f38a2a6',
        "native_storage_pool_id": "SRP_1",
        "description": "fake storage Pool",
        "status": "normal",
        "storage_type": "block",
        "total_capacity": 26300318136401,
        "used_capacity": 19054536509358,
        "free_capacity": 7245781627043,
        'subscribed_capacity': 219902325555200
    }


def fake_storage_get_exception(ctx, storage_id):
    raise exception.StorageNotFound('abcd-1234-5678')


def fake_getcmd_exception(auth_data, transport_target, *var_names, **kwargs):
    return "Connection failed", None, None, None


def fake_getcmd_success(auth_data, transport_target, *var_names, **kwargs):
    return None, None, None, None
