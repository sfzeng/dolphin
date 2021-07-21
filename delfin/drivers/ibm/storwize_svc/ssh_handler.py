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
import time

import paramiko
import six
from oslo_log import log as logging
from oslo_utils import units

from delfin import exception, utils
from delfin.common import constants, alert_util
from delfin.drivers.utils.ssh_client import SSHPool

LOG = logging.getLogger(__name__)


class SSHHandler(object):
    OID_ERR_ID = '1.3.6.1.4.1.2.6.190.4.3'
    OID_SEQ_NUMBER = '1.3.6.1.4.1.2.6.190.4.9'
    OID_LAST_TIME = '1.3.6.1.4.1.2.6.190.4.10'
    OID_OBJ_TYPE = '1.3.6.1.4.1.2.6.190.4.11'
    OID_OBJ_NAME = '1.3.6.1.4.1.2.6.190.4.17'
    OID_SEVERITY = '1.3.6.1.6.3.1.1.4.1.0'

    TRAP_SEVERITY_MAP = {
        '1.3.6.1.4.1.2.6.190.1': constants.Severity.CRITICAL,
        '1.3.6.1.4.1.2.6.190.2': constants.Severity.WARNING,
        '1.3.6.1.4.1.2.6.190.3': constants.Severity.INFORMATIONAL,
    }

    SEVERITY_MAP = {"warning": "Warning",
                    "informational": "Informational",
                    "error": "Major"
                    }

    DISK_PHYSICAL_TYPE = {
        'fc': constants.DiskPhysicalType.FC,
        'sas_direct': constants.DiskPhysicalType.SAS
    }

    SECONDS_TO_MS = 1000
    ALERT_NOT_FOUND_CODE = 'CMMVC8275E'

    def __init__(self, **kwargs):
        self.ssh_pool = SSHPool(**kwargs)

    @staticmethod
    def handle_split(split_str, split_char, arr_number):
        split_value = ''
        if split_str is not None and split_str != '':
            tmp_value = split_str.split(split_char, 1)
            if arr_number == 1 and len(tmp_value) > 1:
                split_value = tmp_value[arr_number].strip()
            elif arr_number == 0:
                split_value = tmp_value[arr_number].strip()
        return split_value

    @staticmethod
    def parse_alert(alert):
        try:
            alert_model = dict()
            alert_name = SSHHandler.handle_split(alert.get(
                SSHHandler.OID_ERR_ID), ':', 1)
            error_info = SSHHandler.handle_split(alert.get(
                SSHHandler.OID_ERR_ID), ':', 0)
            alert_id = SSHHandler.handle_split(error_info, '=', 1)
            severity = SSHHandler.TRAP_SEVERITY_MAP.get(
                alert.get(SSHHandler.OID_SEVERITY),
                constants.Severity.INFORMATIONAL
            )
            alert_model['alert_id'] = str(alert_id)
            alert_model['alert_name'] = alert_name
            alert_model['severity'] = severity
            alert_model['category'] = constants.Category.FAULT
            alert_model['type'] = constants.EventType.EQUIPMENT_ALARM
            alert_model['sequence_number'] = SSHHandler. \
                handle_split(alert.get(SSHHandler.OID_SEQ_NUMBER), '=', 1)
            timestamp = SSHHandler. \
                handle_split(alert.get(SSHHandler.OID_LAST_TIME), '=', 1)
            time_type = '%a %b %d %H:%M:%S %Y'
            occur_time = int(time.mktime(time.strptime(
                timestamp,
                time_type)))
            alert_model['occur_time'] = int(occur_time * SSHHandler.
                                            SECONDS_TO_MS)
            alert_model['description'] = alert_name
            alert_model['resource_type'] = SSHHandler.handle_split(
                alert.get(SSHHandler.OID_OBJ_TYPE), '=', 1)
            alert_model['location'] = SSHHandler.handle_split(alert.get(
                SSHHandler.OID_OBJ_NAME), '=', 1)
            return alert_model
        except Exception as e:
            LOG.error(e)
            msg = ("Failed to build alert model as some attributes missing "
                   "in alert message:%s.") % (six.text_type(e))
            raise exception.InvalidResults(msg)

    def login(self):
        try:
            with self.ssh_pool.item() as ssh:
                result = SSHHandler.do_exec('lssystem', ssh)
                if 'is not a recognized command' in result:
                    raise exception.InvalidIpOrPort()
        except Exception as e:
            LOG.error("Failed to login ibm storwize_svc %s" %
                      (six.text_type(e)))
            raise e

    @staticmethod
    def do_exec(command_str, ssh):
        """Execute command"""
        try:
            utils.check_ssh_injection(command_str)
            if command_str is not None and ssh is not None:
                stdin, stdout, stderr = ssh.exec_command(command_str)
                res, err = stdout.read(), stderr.read()
                re = res if res else err
                result = re.decode()
        except paramiko.AuthenticationException as ae:
            LOG.error('doexec Authentication error:{}'.format(ae))
            raise exception.InvalidUsernameOrPassword()
        except Exception as e:
            err = six.text_type(e)
            LOG.error('doexec InvalidUsernameOrPassword error')
            if 'timed out' in err:
                raise exception.SSHConnectTimeout()
            elif 'No authentication methods available' in err \
                    or 'Authentication failed' in err:
                raise exception.InvalidUsernameOrPassword()
            elif 'not a valid RSA private key file' in err:
                raise exception.InvalidPrivateKey()
            else:
                raise exception.SSHException(err)
        return result

    def exec_ssh_command(self, command):
        try:
            with self.ssh_pool.item() as ssh:
                ssh_info = SSHHandler.do_exec(command, ssh)
            return ssh_info
        except Exception as e:
            msg = "Failed to ssh ibm storwize_svc %s: %s" % \
                  (command, six.text_type(e))
            raise exception.SSHException(msg)

    def change_capacity_to_bytes(self, unit):
        unit = unit.upper()
        if unit == 'TB':
            result = units.Ti
        elif unit == 'GB':
            result = units.Gi
        elif unit == 'MB':
            result = units.Mi
        elif unit == 'KB':
            result = units.Ki
        else:
            result = 1
        return int(result)

    def parse_string(self, value):
        capacity = 0
        if value:
            if value.isdigit():
                capacity = float(value)
            else:
                unit = value[-2:]
                capacity = float(value[:-2]) * int(
                    self.change_capacity_to_bytes(unit))
        return capacity

    def get_storage(self):
        try:
            system_info = self.exec_ssh_command('lssystem')
            storage_map = {}
            self.handle_detail(system_info, storage_map, split=' ')
            serial_number = storage_map.get('id')
            status = 'normal' if storage_map.get('statistics_status') == 'on' \
                else 'offline'
            location = storage_map.get('location')
            free_capacity = self.parse_string(storage_map.get(
                'total_free_space'))
            used_capacity = self.parse_string(storage_map.get(
                'total_used_capacity'))
            raw_capacity = self.parse_string(storage_map.get(
                'total_mdisk_capacity'))
            subscribed_capacity = self.parse_string(storage_map.get(
                'virtual_capacity'))
            firmware_version = ''
            if storage_map.get('code_level') is not None:
                firmware_version = storage_map.get('code_level').split(' ')[0]
            s = {
                'name': storage_map.get('name'),
                'vendor': 'IBM',
                'model': storage_map.get('product_name'),
                'status': status,
                'serial_number': serial_number,
                'firmware_version': firmware_version,
                'location': location,
                'total_capacity': int(free_capacity + used_capacity),
                'raw_capacity': int(raw_capacity),
                'subscribed_capacity': int(subscribed_capacity),
                'used_capacity': int(used_capacity),
                'free_capacity': int(free_capacity)
            }
            return s
        except exception.DelfinException as e:
            err_msg = "Failed to get storage: %s" % (six.text_type(e.msg))
            LOG.error(err_msg)
            raise e
        except Exception as err:
            err_msg = "Failed to get storage: %s" % (six.text_type(err))
            LOG.error(err_msg)
            raise exception.InvalidResults(err_msg)

    def handle_detail(self, deltail_info, detail_map, split):
        detail_arr = deltail_info.split('\n')
        for detail in detail_arr:
            if detail is not None and detail != '':
                strinfo = detail.split(split, 1)
                key = strinfo[0]
                value = ''
                if len(strinfo) > 1:
                    value = strinfo[1]
                detail_map[key] = value

    def list_storage_pools(self, storage_id):
        try:
            pool_list = []
            pool_info = self.exec_ssh_command('lsmdiskgrp')
            pool_res = pool_info.split('\n')
            for i in range(1, len(pool_res)):
                if pool_res[i] is None or pool_res[i] == '':
                    continue

                pool_str = ' '.join(pool_res[i].split())
                strinfo = pool_str.split(' ')
                detail_command = 'lsmdiskgrp %s' % strinfo[0]
                deltail_info = self.exec_ssh_command(detail_command)
                pool_map = {}
                self.handle_detail(deltail_info, pool_map, split=' ')
                status = 'normal' if pool_map.get('status') == 'online' \
                    else 'offline'
                total_cap = self.parse_string(pool_map.get('capacity'))
                free_cap = self.parse_string(pool_map.get('free_capacity'))
                used_cap = self.parse_string(pool_map.get('used_capacity'))
                subscribed_capacity = self.parse_string(pool_map.get(
                    'virtual_capacity'))
                p = {
                    'name': pool_map.get('name'),
                    'storage_id': storage_id,
                    'native_storage_pool_id': pool_map.get('id'),
                    'description': '',
                    'status': status,
                    'storage_type': constants.StorageType.BLOCK,
                    'subscribed_capacity': int(subscribed_capacity),
                    'total_capacity': int(total_cap),
                    'used_capacity': int(used_cap),
                    'free_capacity': int(free_cap)
                }
                pool_list.append(p)

            return pool_list
        except exception.DelfinException as e:
            err_msg = "Failed to get storage pool: %s" % (six.text_type(e))
            LOG.error(err_msg)
            raise e
        except Exception as err:
            err_msg = "Failed to get storage pool: %s" % (six.text_type(err))
            LOG.error(err_msg)
            raise exception.InvalidResults(err_msg)

    def list_volumes(self, storage_id):
        try:
            volume_list = []
            volume_info = self.exec_ssh_command('lsvdisk')
            volume_res = volume_info.split('\n')
            for i in range(1, len(volume_res)):
                if volume_res[i] is None or volume_res[i] == '':
                    continue
                volume_str = ' '.join(volume_res[i].split())
                strinfo = volume_str.split(' ')
                volume_name = strinfo[1]
                detail_command = 'lsvdisk -delim : %s' % volume_name
                deltail_info = self.exec_ssh_command(detail_command)
                volume_map = {}
                self.handle_detail(deltail_info, volume_map, split=':')
                status = 'normal' if volume_map.get('status') == 'online' \
                    else 'offline'
                volume_type = 'thin' if volume_map.get('se_copy') == 'yes' \
                    else 'thick'
                total_capacity = self.parse_string(volume_map.get('capacity'))
                free_capacity = self.parse_string(volume_map.
                                                  get('free_capacity'))
                used_capacity = self.parse_string(volume_map.
                                                  get('used_capacity'))
                compressed = True
                deduplicated = True
                if volume_map.get('compressed_copy') == 'no':
                    compressed = False
                if volume_map.get('deduplicated_copy') == 'no':
                    deduplicated = False

                v = {
                    'name': volume_map.get('name'),
                    'storage_id': storage_id,
                    'description': '',
                    'status': status,
                    'native_volume_id': str(volume_map.get('id')),
                    'native_storage_pool_id': volume_map.get('mdisk_grp_id'),
                    'wwn': str(volume_map.get('vdisk_UID')),
                    'type': volume_type,
                    'total_capacity': int(total_capacity),
                    'used_capacity': int(used_capacity),
                    'free_capacity': int(free_capacity),
                    'compressed': compressed,
                    'deduplicated': deduplicated
                }
                volume_list.append(v)

            return volume_list
        except exception.DelfinException as e:
            err_msg = "Failed to get storage volume: %s" % (six.text_type(e))
            LOG.error(err_msg)
            raise e
        except Exception as err:
            err_msg = "Failed to get storage volume: %s" % (six.text_type(err))
            LOG.error(err_msg)
            raise exception.InvalidResults(err_msg)

    def list_alerts(self, query_para):
        try:
            alert_list = []
            alert_info = self.exec_ssh_command('lseventlog -monitoring yes '
                                               '-message no')
            alert_res = alert_info.split('\n')
            for i in range(1, len(alert_res)):
                if alert_res[i] is None or alert_res[i] == '':
                    continue
                alert_str = ' '.join(alert_res[i].split())
                strinfo = alert_str.split(' ', 1)
                detail_command = 'lseventlog %s' % strinfo[0]
                deltail_info = self.exec_ssh_command(detail_command)
                alert_map = {}
                self.handle_detail(deltail_info, alert_map, split=' ')
                occur_time = int(alert_map.get('last_timestamp_epoch')) * \
                    self.SECONDS_TO_MS
                if not alert_util.is_alert_in_time_range(query_para,
                                                         occur_time):
                    continue
                alert_name = alert_map.get('event_id_text', '')
                event_id = alert_map.get('event_id')
                location = alert_map.get('object_name', '')
                resource_type = alert_map.get('object_type', '')
                severity = self.SEVERITY_MAP.get(alert_map.
                                                 get('notification_type'))
                if severity == 'Informational' or severity is None:
                    continue
                alert_model = {
                    'alert_id': event_id,
                    'alert_name': alert_name,
                    'severity': severity,
                    'category': constants.Category.FAULT,
                    'type': 'EquipmentAlarm',
                    'sequence_number': alert_map.get('sequence_number'),
                    'occur_time': occur_time,
                    'description': alert_name,
                    'resource_type': resource_type,
                    'location': location
                }
                alert_list.append(alert_model)

            return alert_list
        except exception.DelfinException as e:
            err_msg = "Failed to get storage alert: %s" % (six.text_type(e))
            LOG.error(err_msg)
            raise e
        except Exception as err:
            err_msg = "Failed to get storage alert: %s" % (six.text_type(err))
            LOG.error(err_msg)
            raise exception.InvalidResults(err_msg)

    def fix_alert(self, alert):
        command_line = 'cheventlog -fix %s' % alert
        result = self.exec_ssh_command(command_line)
        if result:
            if self.ALERT_NOT_FOUND_CODE not in result:
                raise exception.InvalidResults(six.text_type(result))
            LOG.warning("Alert %s doesn't exist.", alert)

    def list_controllers(self, storage_id):
        try:
            controller_list = []
            control_info = self.exec_ssh_command('lscontroller')
            control_res = control_info.split('\n')
            for i in range(1, len(control_res)):
                if control_res[i] is None or control_res[i] == '':
                    continue
                control_str = ' '.join(control_res[i].split())
                str_info = control_str.split(' ')
                control_id = str_info[0]
                detail_command = 'lscontroller %s' % control_id
                deltail_info = self.exec_ssh_command(detail_command)
                control_map = {}
                self.handle_detail(deltail_info, control_map, split=' ')
                status = constants.ControllerStatus.NORMAL
                if control_map.get('degraded') == 'yes':
                    status = constants.ControllerStatus.DEGRADED
                soft_version = '%s %s' % (control_map.get('vendor_id'),
                                          control_map.get('product_id_low'))
                controller_result = {
                    'name': control_map.get('controller_name'),
                    'storage_id': storage_id,
                    'native_controller_id': control_map.get('id'),
                    'status': status,
                    'soft_version': soft_version,
                    'location': control_map.get('controller_name')
                }
                controller_list.append(controller_result)
            return controller_list
        except Exception as err:
            err_msg = "Failed to get controller attributes from Storwize: %s"\
                      % (six.text_type(err))
            LOG.error(err_msg)
            raise exception.InvalidResults(err_msg)

    def list_disks(self, storage_id):
        try:
            disk_list = []
            disk_info = self.exec_ssh_command('lsmdisk')
            disk_res = disk_info.split('\n')
            for i in range(1, len(disk_res)):
                if disk_res[i] is None or disk_res[i] == '':
                    continue
                control_str = ' '.join(disk_res[i].split())
                str_info = control_str.split(' ')
                disk_id = str_info[0]
                detail_command = 'lsmdisk %s' % disk_id
                deltail_info = self.exec_ssh_command(detail_command)
                disk_map = {}
                self.handle_detail(deltail_info, disk_map, split=' ')
                status = constants.DiskStatus.NORMAL
                if disk_map.get('status') == 'offline':
                    status = constants.DiskStatus.OFFLINE
                physical_type = SSHHandler.DISK_PHYSICAL_TYPE.get(
                    disk_map.get('fabric_type'),
                    constants.DiskPhysicalType.UNKNOWN)
                location = '%s_%s' % (disk_map.get('controller_name'),
                                      disk_map.get('name'))
                disk_result = {
                    'name': disk_map.get('name'),
                    'storage_id': storage_id,
                    'native_disk_id': disk_map.get('id'),
                    'capacity': int(self.parse_string(
                        disk_map.get('capacity'))),
                    'status': status,
                    'physical_type': physical_type,
                    'native_disk_group_id': disk_map.get('mdisk_grp_name'),
                    'location': location
                }
                disk_list.append(disk_result)
            return disk_list
        except Exception as err:
            err_msg = "Failed to get disk attributes from Storwize: %s" % \
                      (six.text_type(err))
            raise exception.InvalidResults(err_msg)

    def get_fc_port(self, storage_id):
        port_list = []
        fc_info = self.exec_ssh_command('lsportfc')
        fc_res = fc_info.split('\n')
        for i in range(1, len(fc_res)):
            if fc_res[i] is None or fc_res[i] == '':
                continue
            control_str = ' '.join(fc_res[i].split())
            str_info = control_str.split(' ')
            port_id = str_info[0]
            detail_command = 'lsportfc %s' % port_id
            deltail_info = self.exec_ssh_command(detail_command)
            port_map = {}
            self.handle_detail(deltail_info, port_map, split=' ')
            status = constants.PortHealthStatus.NORMAL
            conn_status = constants.PortConnectionStatus.CONNECTED
            if port_map.get('status') != 'active':
                status = constants.PortHealthStatus.ABNORMAL
                conn_status = constants.PortConnectionStatus.DISCONNECTED
            port_type = constants.PortType.FC
            if port_map.get('type') == 'ethernet':
                port_type = constants.PortType.ETH
            location = '%s_%s' % (port_map.get('node_name'),
                                  port_map.get('id'))
            speed = None
            if port_map.get('port_speed')[:-2].isdigit():
                speed = int(self.parse_string(port_map.get('port_speed')))
            port_result = {
                'name': port_map.get('id'),
                'storage_id': storage_id,
                'native_port_id': port_map.get('id'),
                'location': location,
                'connection_status': conn_status,
                'health_status': status,
                'type': port_type,
                'max_speed': speed,
                'native_parent_id': port_map.get('node_name'),
                'wwn': port_map.get('WWPN')
            }
            port_list.append(port_result)
        return port_list

    def get_iscsi_port(self, storage_id):
        port_list = []
        for i in range(1, 3):
            port_array = []
            port_command = 'lsportip %s' % i
            port_info = self.exec_ssh_command(port_command)
            port_arr = port_info.split('\n')
            port_map = {}
            for detail in port_arr:
                if detail is not None and detail != '':
                    strinfo = detail.split(' ', 1)
                    key = strinfo[0]
                    value = ''
                    if len(strinfo) > 1:
                        value = strinfo[1]
                    port_map[key] = value
                else:
                    if len(port_map) > 1:
                        port_array.append(port_map)
                        port_map = {}
                        continue
            for port in port_array:
                if port.get('failover') == 'yes':
                    continue
                status = constants.PortHealthStatus.ABNORMAL
                if port.get('state') == 'online':
                    status = constants.PortHealthStatus.NORMAL
                conn_status = constants.PortConnectionStatus.DISCONNECTED
                if port.get('link_state') == 'active':
                    conn_status = constants.PortConnectionStatus.CONNECTED
                port_type = constants.PortType.ETH
                location = '%s_%s' % (port.get('node_name'),
                                      port.get('id'))
                port_result = {
                    'name': location,
                    'storage_id': storage_id,
                    'native_port_id': location,
                    'location': location,
                    'connection_status': conn_status,
                    'health_status': status,
                    'type': port_type,
                    'max_speed': int(self.handle_port_bps(port.get('speed'))),
                    'native_parent_id': port.get('node_name'),
                    'mac_address': port.get('MAC'),
                    'ipv4': port.get('IP_address'),
                    'ipv4_mask': port.get('mask'),
                    'ipv6': port.get('IP_address_6')
                }
                port_list.append(port_result)
        return port_list

    def handle_port_bps(self, value):
        speed = 0
        if value:
            if value.isdigit():
                speed = float(value)
            else:
                unit = value[-4:-2]
                speed = float(value[:-4]) * int(
                    self.change_capacity_to_bytes(unit))
        return speed

    def list_ports(self, storage_id):
        try:
            port_list = []
            port_list.extend(self.get_fc_port(storage_id))
            port_list.extend(self.get_iscsi_port(storage_id))
            return port_list
        except Exception as err:
            err_msg = "Failed to get ports attributes from Storwize: %s" % \
                      (six.text_type(err))
            raise exception.InvalidResults(err_msg)
