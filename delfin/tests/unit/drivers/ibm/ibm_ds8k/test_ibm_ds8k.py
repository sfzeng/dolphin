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
import sys
from unittest import TestCase, mock

sys.modules['delfin.cryptor'] = mock.Mock()

from delfin import context
from delfin.drivers.ibm.ds8k.rest_handler import RestHandler
from delfin.drivers.ibm.ds8k.ds8k import DS8KDriver


class Request:
    def __init__(self):
        self.environ = {'delfin.context': context.RequestContext()}
        pass


ACCESS_INFO = {
    "storage_id": "12345",
    "rest": {
        "host": "110.143.132.231",
        "port": "8443",
        "username": "username",
        "password": "cGFzc3dvcmQ="
    },
    "ssh": {
        "host": "110.143.132.231",
        "port": "22",
        "username": "username",
        "password": "password",
        "host_key": "weqewrerwerwerwe"
    },
    "vendor": "IBM",
    "model": "DS8000",
    "extra_attributes": {
        "array_id": "00112233"
    }
}
GET_STORAGE = {
    "data": {
        "systems": [
            {
                "id": "2107-75BXG71",
                "name": "TDCUOB_DS8870",
                "state": "online",
                "release": "7.5.1",
                "bundle": "87.51.103.5120",
                "MTM": "2423-961",
                "sn": "75BXG71",
                "wwnn": "5005076304FFD7EF",
                "cap": "1655709892608",
                "capalloc": "1073741824000",
                "capavail": "581968068608",
                "capraw": "2516582400000"
            }
        ]
    }
}
GET_ALL_POOLS = {
    "data": {
        "pools": [
            {
                "id": "P0",
                "link": {
                    "rel": "self",
                    "href": "https:/192.168.1.170:8452/api/v1/pools/P0"
                },
                "name": "test_pool",
                "node": "0",
                "stgtype": "fb",
                "cap": "1655709892608",
                "capalloc": "1073741824000",
                "capavail": "581968068608",
                "overprovisioned": "0.6",
                "easytier": "managed",
                "tieralloc": [
                    {
                        "tier": "ENT",
                        "cap": "1655709892608",
                        "allocated": "1073741824000",
                        "assigned": "0"
                    }
                ],
                "threshold": "15",
                "real_capacity_allocated_on_ese": "0",
                "virtual_capacity_allocated_on_ese": "0",
                "eserep": {},
                "tserep": {},
                "volumes": {
                    "link": {
                        "rel": "self"
                    }
                }
            }
        ]
    }
}
GET_ALL_LUNS = {
    "data": {
        "volumes":
        [
            {
                "link": {
                    "rel": "self",
                    "href": "https://{hmc}:443/api/v1/volumes/0000"
                },
                "id": "0000",
                "name": "mytest",
                "state": "normal",
                "cap": "322122547200",
                "stgtype": "fb",
                "VOLSER": "",
                "lss": {
                    "id": "00",
                    "link": {
                        "rel": "self",
                        "href":
                        "https://{hmc}:443/api/lss/00"
                    }
                },
                "allocmethod": "legacy",
                "tp": "none",
                "capalloc": "134217728",
                "MTM": "2107-900",
                "datatype": "FB 512",
                "tieralloc":
                [
                    {
                        "tier": "ENT",
                        "allocated": "34502"
                    }
                ],
                "pool": {
                    "id": "P2",
                    "link": {
                        "rel": "self",
                        "href":
                        "https://{hmc}:443/api/v1/pools/P2"
                    }
                }
            }
        ]
    }
}
GET_ALL_LUNS_NULL = {
    "data": {
        "volumes":
        []
    }
}
GET_ALL_ALERTS = {
    "data": {
        "events":
        [
            {
                "id": "SEfe",
                "type": "HostPortStateChanged",
                "severity": "error",
                "time": "2014-04-20T13:00:23-0700",
                "resource_id": "1152922127280127616",
                "formatted_parameter":
                    ["10000090FA383E80", "Logged Off",
                     "Logged In", "NISCSIHostPortID: ""IBM.2107-75BXG71/12"],
                "description": "Host port 10000090FA383E80 state logged in."
            }
        ]
    }
}
TOKEN_RESULT = {
    "server": {
        "status": "ok",
        "code": "200",
        "message": "Operation done successfully."
    },
    "token": {
        "token": "ddb1743a",
        "expired_time": "2014-08-25T03:28:15-0700",
        "max_idle_interval": "1800000"
    }
}
TRAP_INFO = {
    "1.3.6.1.2.1.1.3.0": "0",
    '1.3.6.1.6.3.1.1.4.1.0': '1.3.6.1.4.1.1139.103.1.18.2.0',
    '1.3.6.1.4.1.1139.103.1.18.1.1': 'eeeeeeeee',
    '1.3.6.1.4.1.1139.103.1.18.1.3': 'ddddddd',
    '1.3.6.1.4.1.1139.103.1.18.1.4': 'this is test',
    '1.3.6.1.4.1.1139.103.1.18.1.5': '2020/11/20 14:10:10',
    '1.3.6.1.4.1.1139.103.1.18.1.2': 'test'
}
storage_result = {
    'name': 'TDCUOB_DS8870',
    'vendor': 'IBM',
    'model': '2423-961',
    'status': 'normal',
    'serial_number': '75BXG71',
    'firmware_version': '7.5.1',
    'location': '',
    'total_capacity': 1655709892608,
    'raw_capacity': 2516582400000,
    'used_capacity': 1073741824000,
    'free_capacity': 581968068608
}
pool_result = [
    {
        'name': 'test_pool',
        'storage_id': '12345',
        'native_storage_pool_id': 'P0',
        'status': 'abnormal',
        'storage_type': 'block',
        'total_capacity': 1655709892608,
        'used_capacity': 1073741824000,
        'free_capacity': 581968068608
    }
]
volume_result = [
    {
        'name': 'mytest_0000',
        'storage_id': '12345',
        'description': '',
        'status': 'normal',
        'native_volume_id': '0000',
        'native_storage_pool_id': 'P2',
        'wwn': '',
        'type': 'thick',
        'total_capacity': 322122547200,
        'used_capacity': 134217728,
        'free_capacity': 321988329472
    }
]
alert_result = [
    {
        'alert_id': 'HostPortStateChanged',
        'alert_name': 'Host port 10000090FA383E80 state logged in.',
        'severity': 'Critical',
        'description': ['10000090FA383E80', 'Logged Off', 'Logged In',
                        'NISCSIHostPortID: IBM.2107-75BXG71/12'],
        'category': 'Fault',
        'type': 'EquipmentAlarm',
        'sequence_number': 'SEfe',
        'occur_time': 1397970023000,
        'resource_type': 'Storage',
        'location': ''
    }
]

trap_result = {
    'alert_id': 'ddddddd',
    'alert_name': 'test',
    'severity': 'Critical',
    'category': 'Fault',
    'type': 'EquipmentAlarm',
    'occur_time': 1605852610000,
    'description': 'this is test',
    'resource_type': 'Storage',
    'location': 'eeeeeeeee'
}


class TestDS8KDriver(TestCase):

    @mock.patch.object(RestHandler, 'get_storage')
    def test_get_storage(self, mock_storage):
        RestHandler.login = mock.Mock(return_value=None)
        mock_storage.return_value = GET_STORAGE
        storage = DS8KDriver(**ACCESS_INFO).get_storage(context)
        self.assertDictEqual(storage, storage_result)

    @mock.patch.object(RestHandler, 'get_all_pools')
    def test_list_storage_pools(self, mock_pool):
        RestHandler.login = mock.Mock(return_value=None)
        mock_pool.return_value = GET_ALL_POOLS
        pool = DS8KDriver(**ACCESS_INFO).list_storage_pools(context)
        self.assertEqual(pool, pool_result)

    @mock.patch.object(RestHandler, 'get_pool_volumes')
    @mock.patch.object(RestHandler, 'get_all_pools')
    def test_list_volumes(self, mock_pool, mock_vol):
        RestHandler.login = mock.Mock(return_value=None)
        mock_pool.return_value = GET_ALL_POOLS
        mock_vol.return_value = GET_ALL_LUNS
        vol = DS8KDriver(**ACCESS_INFO).list_volumes(context)
        self.assertEqual(vol, volume_result)

    @mock.patch.object(RestHandler, 'get_all_alerts')
    def test_list_alerts(self, mock_alert):
        RestHandler.login = mock.Mock(return_value=None)
        mock_alert.return_value = GET_ALL_ALERTS
        alert = DS8KDriver(**ACCESS_INFO).list_alerts(context)
        alert[0]['occur_time'] = alert_result[0]['occur_time']
        self.assertEqual(alert, alert_result)

    @mock.patch.object(RestHandler, 'call_with_token')
    def test_call_and_login(self, mock_token):
        with self.assertRaises(Exception) as exc:
            mock_token.return_value = mock.MagicMock(
                status_code=401, text='Authentication has failed')
            DS8KDriver(**ACCESS_INFO).rest_handler.login()
        self.assertEqual('Invalid username or password.', str(exc.exception))
        RestHandler.login = mock.Mock(return_value=None)
        mock_token.return_value = mock.MagicMock(status_code=401)
        DS8KDriver(**ACCESS_INFO).rest_handler.call('')
