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

from oslo_log import log

from delfin.common import constants
from delfin.drivers import driver
from delfin.drivers.ibm.ds8k import rest_handler, alert_handler

LOG = log.getLogger(__name__)


class DS8KDriver(driver.StorageDriver):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rest_handler = rest_handler.RestHandler(**kwargs)
        self.rest_handler.login()

    def reset_connection(self, context, **kwargs):
        self.rest_handler.logout()
        self.rest_handler.verify = kwargs.get('verify', False)
        self.rest_handler.login()

    def close_connection(self):
        self.rest_handler.logout()

    def get_storage(self, context):
        system_info = self.rest_handler.get_storage()
        if system_info is not None:
            system_data = system_info.get('data', {}).get('systems')
            for system in system_data:
                name = system.get('name')
                model = system.get('MTM')
                serial_number = system.get('sn')
                version = system.get('release')
                status = constants.StorageStatus.NORMAL
                if system.get('state') != 'online':
                    status = constants.StorageStatus.ABNORMAL
                total = 0
                free = 0
                used = 0
                raw = 0
                if system.get('cap') != '' and system.get('cap') is not None:
                    total = int(system.get('cap'))
                if system.get('capraw') != '' and \
                        system.get('capraw') is not None:
                    raw = int(system.get('capraw'))
                if system.get('capalloc') != '' and \
                        system.get('capalloc') is not None:
                    used = int(system.get('capalloc'))
                if system.get('capavail') != '' and \
                        system.get('capavail') is not None:
                    free = int(system.get('capavail'))
                result = {
                    'name': name,
                    'vendor': 'IBM',
                    'model': model,
                    'status': status,
                    'serial_number': serial_number,
                    'firmware_version': version,
                    'location': '',
                    'total_capacity': total,
                    'raw_capacity': raw,
                    'used_capacity': used,
                    'free_capacity': free
                }
                break
        return result

    def list_storage_pools(self, context):
        pool_info = self.rest_handler.get_all_pools()
        pool_list = []
        status = constants.StoragePoolStatus.NORMAL
        if pool_info is not None:
            pool_data = pool_info.get('data', {}).get('pools')
            for pool in pool_data:
                if pool.get('stgtype') == 'fb':
                    pool_type = constants.StorageType.BLOCK
                else:
                    pool_type = constants.StorageType.FILE
                if (int(pool.get('capalloc')) / int(pool.get('cap'))) * 100 > \
                        int(pool.get('threshold')):
                    status = constants.StoragePoolStatus.ABNORMAL
                pool_result = {
                    'name': pool.get('name'),
                    'storage_id': self.storage_id,
                    'native_storage_pool_id': str(pool.get('id')),
                    'status': status,
                    'storage_type': pool_type,
                    'total_capacity': int(pool.get('cap')),
                    'used_capacity': int(pool.get('capalloc')),
                    'free_capacity': int(pool.get('capavail'))
                }
                pool_list.append(pool_result)
        return pool_list

    def list_volumes(self, context):
        volume_list = []
        pool_list = self.rest_handler.get_all_pools()
        if pool_list is not None:
            pool_data = pool_list.get('data', {}).get('pools')
            for pool in pool_data:
                volumes = self.rest_handler.get_pool_volumes(pool.get('id'))
                if volumes is not None:
                    vol_entries = volumes.get('data', {}).get('volumes')
                    for volume in vol_entries:
                        total = volume.get('cap')
                        used = volume.get('capalloc')
                        vol_type = constants.VolumeType.THIN
                        if volume.get('stgtype') == 'fb':
                            vol_type = constants.VolumeType.THICK
                        if volume.get('state') == 'normal':
                            status = constants.StorageStatus.NORMAL
                        else:
                            status = constants.StorageStatus.ABNORMAL
                        vol_name = '%s_%s' % (volume.get('name'),
                                              volume.get('id'))
                        vol = {
                            'name': vol_name,
                            'storage_id': self.storage_id,
                            'description': '',
                            'status': status,
                            'native_volume_id': str(volume.get('id')),
                            'native_storage_pool_id':
                                volume.get('pool').get('id'),
                            'wwn': '',
                            'type': vol_type,
                            'total_capacity': int(total),
                            'used_capacity': int(used),
                            'free_capacity': int(total) - int(used)
                        }
                        volume_list.append(vol)
        return volume_list

    def list_alerts(self, context, query_para=None):
        alert_model_list = []
        alert_list = self.rest_handler.get_all_alerts()
        alert_handler.AlertHandler() \
            .parse_queried_alerts(alert_model_list, alert_list, query_para)
        return alert_model_list

    def list_controllers(self, context):
        pass

    def list_ports(self, context):
        pass

    def list_disks(self, context):
        pass

    def add_trap_config(self, context, trap_config):
        pass

    def remove_trap_config(self, context, trap_config):
        pass

    @staticmethod
    def parse_alert(context, alert):
        pass

    def clear_alert(self, context, alert):
        pass
