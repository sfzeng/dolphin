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
import time

import paramiko
import six
from oslo_log import log as logging
from delfin.drivers.utils.ssh_client import SSHClient

from delfin import exception

LOG = logging.getLogger(__name__)


class SSHHandler(object):

    login_command = 'help'
    systeminfo_command = 'lssystem'
    poolinfo_command = 'lsmdiskgrp'
    poolinfo_detail_command = 'lsmdiskgrp '
    volumeinfo_command = 'lsvdisk'
    volumeinfo_detail_command = 'lsvdisk -delim : '
    eventlog_command = 'lseventlog -filtervalue "status=alert"'
    alert_detail_command = 'lseventlog '
    enclosure_command = 'lsenclosure -delim :'

    TIME_PATTERN = '%Y%m%d%H%M%S'

    SEVERITY_MAP = {"warning": "Warning",
                    "informational": "Informational",
                    "error": "Critical"
                    }

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def set_storage_id(self, storage_id):
        self.storage_id = storage_id

    def login(self, context):
        """Test SSH connection """
        version = ''
        try:
            ssh_client = SSHClient(**self.kwargs)
            ssh_client.do_exec(context, SSHHandler.login_command)
        except Exception:
            raise exception.SSHException(
                reason='Failed to ssh ibmv7000')
        return version

    def unitstobytes(self, unit):
        result = 0
        if unit == 'TB':
            result = 1024 * 1024 * 1024 * 1024
        elif unit == 'GB':
            result = 1024 * 1024 * 1024
        elif unit == 'MB':
            result = 1024 * 1024
        elif unit == 'KB':
            result = 1024
        else:
            result = 1
        return int(result)

    def do_exec(self, context, command_str, ssh_client):
        """Execute command"""
        re = None
        try:
            if command_str is not None:
                re = ssh_client.exec_command(command_str)
        except paramiko.AuthenticationException as ae:
            LOG.error('doexec Authentication error:{}'.format(ae))
            raise exception.InvalidUsernameOrPassword()
        except Exception as e:
            LOG.error('doexec InvalidUsernameOrPassword error:{}'.format(e))
            if 'WSAETIMEDOUT' in str(e):
                raise exception.SSHConnectTimeout()
            elif 'No authentication methods available' in str(e) \
                    or 'Authentication failed' in str(e):
                raise exception.SSHInvalidUsernameOrPassword()
            elif 'not a valid RSA private key file' in str(e):
                raise exception.InvalidPrivateKey()
            elif 'not found in known_hosts' in str(e):
                raise exception.SSHNotFoundKnownHosts(ssh_client.ssh_host)
            else:
                raise exception.SSHException()

        return re

    def handle_ssh(self, context, command, method):
        try:
            ssh_client = SSHClient(**self.kwargs)
            ssh_info = ssh_client. \
                do_exec(command)
            return ssh_info
        except Exception as e:
            msg = "Failed to ssh ibmv7000 %s: %s" % (method, six.text_type(e))
            raise exception.SSHException(msg)

    def handle_detail_ssh(self, context, ssh_client, command, method):
        try:
            ssh_info = self.do_exec(context, command, ssh_client)
            return ssh_info
        except Exception as e:
            msg = "Failed to ssh ibmv7000 %s: %s" % (method, six.text_type(e))
            raise exception.SSHException(msg)

    def handle_capacity(self, value):
        capacity = 0
        if value:
            unit = value[-2:]
            capacity = float(value[:-2]) * int(self.unitstobytes(unit))
        return capacity

    def get_storage(self, context):
        try:
            systeminfo = ''
            systeminfo = self.handle_ssh(context,
                                         self.systeminfo_command, 'storage')
            enclosure_info = self.handle_ssh(context, self.enclosure_command,
                                             'enclosure')
            enclosure_res = enclosure_info.split('\n')
            enclosure = enclosure_res[1].split(':')
            serial_number = enclosure[7]
            map = {}
            self.handle_detail(systeminfo, map, split=' ')

            status = map.get('statistics_status') == 'on' and 'normal' or \
                'offline'
            location = map.get('location')
            free_capacity = self.handle_capacity(map.get(
                'total_free_space'))
            used_capacity = self.handle_capacity(map.get(
                'total_used_capacity'))
            raw_capacity = self.handle_capacity(map.get(
                'total_drive_raw_capacity'))
            subscribed_capacity = self.handle_capacity(map.get(
                'total_allocated_extent_capacity'))
            s = {
                'name': map.get('name'),
                'vendor': 'IBM',
                'model': 'IBM V7000',
                'status': status,
                'serial_number': serial_number,
                'firmware_version': '',
                'location': location,
                'total_capacity': int(free_capacity + used_capacity),
                'raw_capacity': int(raw_capacity),
                'subscribed_capacity': int(subscribed_capacity),
                'used_capacity': int(used_capacity),
                'free_capacity': int(free_capacity)
            }
            return s
        except exception.DelfinException as e:
            err_msg = "Failed to get storage: %s" % (e.msg)
            LOG.error(err_msg)
            raise e
        except Exception as err:
            err_msg = "Failed to get storage: %s" % (six.text_type(err))
            LOG.error(err_msg)
            raise exception.InvalidResults(err_msg)

    def handle_detail(self, deltail_info, map, split):
        detail_arr = deltail_info.split('\n')
        for detail in detail_arr:
            if detail is not None and detail != '':
                strinfo = detail.split(split, 1)
                key = strinfo[0]
                value = strinfo[1] and strinfo[1] or ''
                map[key] = value

    def list_storage_pools(self, context):
        try:
            pool_list = []
            poolinfo = ''
            ssh_client = SSHClient(**self.kwargs)
            ssh_client.connect()
            poolinfo = self.handle_detail_ssh(context, ssh_client,
                                              self.poolinfo_command, 'pool')
            pool_res = poolinfo.split('\n')
            i = 1
            while i < len(pool_res):
                if pool_res[i] is None or pool_res[i] == '':
                    i = i + 1
                    continue

                pool_str = ' '.join(pool_res[i].split())
                strinfo = pool_str.split(' ')
                detail_command = \
                    SSHHandler.poolinfo_detail_command + strinfo[0]
                deltail_info = self.handle_detail_ssh(
                    context, ssh_client, detail_command, 'pooldetail')
                map = {}
                self.handle_detail(deltail_info, map, split=' ')
                status = map.get('status') == 'online' and 'normal' or \
                    'offline'
                total_cap = self.handle_capacity(map.get('capacity'))
                free_cap = self.handle_capacity(map.get('free_capacity'))
                used_cap = self.handle_capacity(map.get('used_capacity'))
                subscribed_cap = self.handle_capacity(map.get('real_capacity'))
                p = {
                    'name': map.get('name'),
                    'storage_id': self.storage_id,
                    'native_storage_pool_id': map.get('id'),
                    'description': '',
                    'status': status,
                    'storage_type': 'file',
                    'total_capacity': int(total_cap),
                    'subscribed_capacity': int(subscribed_cap),
                    'used_capacity': int(used_cap),
                    'free_capacity': int(free_cap)
                }
                pool_list.append(p)
                i = i + 1

            return pool_list
        except exception.DelfinException as e:
            err_msg = "Failed to get storage pool: %s" % (e.msg)
            LOG.error(err_msg)
            raise e
        except Exception as err:
            err_msg = "Failed to get storage pool: %s" % (six.text_type(err))
            LOG.error(err_msg)
            raise exception.InvalidResults(err_msg)
        finally:
            ssh_client.close()

    def list_volumes(self, context):
        try:
            volume_list = []
            ssh_client = SSHClient(**self.kwargs)
            ssh_client.connect()
            volumeinfo = self.handle_detail_ssh(
                context, ssh_client, self.volumeinfo_command, 'volume')
            volume_res = volumeinfo.split('\n')
            i = 1
            while i < len(volume_res):
                if volume_res[i] is None or volume_res[i] == '':
                    i = i + 1
                    continue
                volume_str = ' '.join(volume_res[i].split())
                strinfo = volume_str.split(' ')
                volume_name = strinfo[1]
                detail_command = \
                    SSHHandler.volumeinfo_detail_command + volume_name
                deltail_info = self.handle_detail_ssh(
                    context, ssh_client, detail_command, 'volumedetail')
                map = {}
                self.handle_detail(deltail_info, map, split=':')
                status = map.get('status') == 'online' and 'normal' or \
                    'offline'
                volume_type = map.get('se_copy') == 'yes' and 'thin' or 'thick'
                total_capacity = self.handle_capacity(map.get('capacity'))
                free_capacity = self.handle_capacity(map.get('free_capacity'))
                used_capacity = self.handle_capacity(map.get('used_capacity'))
                compressed = True
                deduplicated = True
                if map.get('compressed_copy') == 'no':
                    compressed = False
                if map.get('deduplicated_copy') == 'no':
                    deduplicated = False

                v = {
                    'name': map.get('name'),
                    'storage_id': self.storage_id,
                    'description': '',
                    'status': status,
                    'native_volume_id': str(map.get('id')),
                    'native_storage_pool_id': map.get('mdisk_grp_id'),
                    'wwn': '',
                    'type': volume_type,
                    'total_capacity': int(total_capacity),
                    'used_capacity': int(used_capacity),
                    'free_capacity': int(free_capacity),
                    'compressed': compressed,
                    'deduplicated': deduplicated
                }
                volume_list.append(v)
                i = i + 1

            return volume_list
        except exception.DelfinException as e:
            err_msg = "Failed to get storage volume: %s" % (e.msg)
            LOG.error(err_msg)
            raise e
        except Exception as err:
            err_msg = "Failed to get storage volume: %s" % (six.text_type(err))
            LOG.error(err_msg)
            raise exception.InvalidResults(err_msg)
        finally:
            ssh_client.close()

    def judge_alert_time(self, map, query_para):
        if len(map) <= 1:
            return False
        if query_para is None and len(map) > 1:
            return True
        occur_time = self.get_time_stamp(map.get('last_timestamp'))
        if query_para.get('begin_time') and query_para.get('end_time'):
            if occur_time >= int(query_para.get('begin_time')) and \
                    occur_time <= int(query_para.get('end_time')):
                return True
        if query_para.get('begin_time'):
            if occur_time >= int(query_para.get('begin_time')):
                return True
        if query_para.get('end_time'):
            if occur_time <= int(query_para.get('end_time')):
                return True
        return False

    def list_alerts(self, context, query_para):
        try:
            alert_list = []
            alertinfo = ''
            ssh_client = SSHClient(**self.kwargs)
            ssh_client.connect()
            alertinfo = self.handle_detail_ssh(
                context, ssh_client, self.eventlog_command, 'volume')
            alert_res = alertinfo.split('\n')
            i = 1
            while i < len(alert_res):
                if alert_res[i] is None or alert_res[i] == '':
                    i = i + 1
                    continue
                alert_str = ' '.join(alert_res[i].split())
                strinfo = alert_str.split(' ', 9)
                alert_id = strinfo[0]
                detail_command = \
                    SSHHandler.alert_detail_command + strinfo[0]
                deltail_info = self.handle_detail_ssh(
                    context, ssh_client, detail_command, 'alertdetail')
                map = {}
                self.handle_detail(deltail_info, map, split=' ')
                if self.judge_alert_time(map, query_para) is False:
                    i = i + 1
                    continue
                time_str = '20%s' % map.get('last_timestamp')
                time_stamp = self.get_time_stamp(time_str)
                alert_name = map.get('error_code_text') and map.get(
                    'error_code_text') or ''
                err_code = map.get('error_code') and map.get('error_code') or \
                    ''
                location = map.get('object_name') and map.get('object_name') \
                    or ''
                resource_type = map.get('object_type') and map.get(
                    'object_type') or ''
                severity = self.SEVERITY_MAP.get(map.get('notification_type'))

                alert_model = {
                    'alert_id': err_code,
                    'alert_name': alert_name,
                    'severity': severity,
                    'category': 'Fault',
                    'type': 'EquipmentAlarm',
                    'sequence_number': alert_id,
                    'occur_time': time_stamp,
                    'description': alert_name,
                    'resource_type': resource_type,
                    'location': location
                }
                alert_list.append(alert_model)
                i = i + 1

            return alert_list
        except exception.DelfinException as e:
            err_msg = "Failed to get storage alert: %s" % (e.msg)
            LOG.error(err_msg)
            raise e
        except Exception as err:
            err_msg = "Failed to get storage alert: %s" % (six.text_type(err))
            LOG.error(err_msg)
            raise exception.InvalidResults(err_msg)
        finally:
            ssh_client.close()

    def get_time_stamp(self, time_str):
        """ Time stamp to time conversion
        """
        time_stamp = ''
        try:
            if time_str is not None:
                time_array = time.strptime(time_str, SSHHandler.TIME_PATTERN)
                time_stamp = int(time.mktime(time_array) * 1000)
        except Exception as e:
            LOG.error(e)

        return time_stamp
