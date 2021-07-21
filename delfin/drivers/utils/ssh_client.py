# Copyright 2020 The SODA Authors.
# Copyright 2011 OpenStack LLC
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
import paramiko
import six
from eventlet import pools
from oslo_log import log as logging
from paramiko.hostkeys import HostKeyEntry

from delfin import cryptor
from delfin import exception, utils

LOG = logging.getLogger(__name__)


class SSHClient(object):
    SOCKET_TIMEOUT = 10

    def __init__(self, **kwargs):
        ssh_access = kwargs.get('ssh')
        if ssh_access is None:
            raise exception.InvalidInput('Input ssh_access is missing')
        self.ssh_host = ssh_access.get('host')
        self.ssh_port = ssh_access.get('port')
        self.ssh_username = ssh_access.get('username')
        self.ssh_password = ssh_access.get('password')
        self.ssh_pub_key_type = ssh_access.get('pub_key_type')
        self.ssh_pub_key = ssh_access.get('pub_key')
        self.ssh_conn_timeout = ssh_access.get('conn_timeout')
        if self.ssh_conn_timeout is None:
            self.ssh_conn_timeout = SSHClient.SOCKET_TIMEOUT

    def connect(self):
        self.ssh = paramiko.SSHClient()

        if self.ssh_pub_key is None:
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        else:
            host_key = '%s %s %s' % \
                       (self.ssh_host, self.ssh_pub_key_type, self.ssh_pub_key)
            self.set_host_key(host_key)

        self.ssh.connect(hostname=self.ssh_host, port=self.ssh_port,
                         username=self.ssh_username,
                         password=cryptor.decode(self.ssh_password),
                         timeout=self.ssh_conn_timeout)

    def set_host_key(self, host_key):
        """
        Set public key,because input kwargs parameter host_key is string,
        not a file path,we can not use load file to get public key,so we set
        it as a string.
        :param str host_key: the public key which as a string
        """
        if (len(host_key) == 0) or (host_key[0] == "#"):
            return
        try:
            e = HostKeyEntry.from_line(host_key)
        except exception.SSHException:
            return
        if e is not None:
            host_names = e.hostnames
            for h in host_names:
                if self.ssh._host_keys.check(h, e.key):
                    e.hostnames.remove(h)
            if len(e.hostnames):
                self.ssh._host_keys._entries.append(e)

    def exec_command(self, command_str):
        result = None
        try:
            if command_str is not None:
                if self.ssh is not None:
                    stdin, stdout, stderr = self.ssh.exec_command(command_str)
                    res, err = stdout.read(), stderr.read()
                    re = res if res else err
                    result = re.decode()
        except Exception as e:
            LOG.error(e)
            result = e
        return result

    def close(self):
        try:
            if self.ssh is not None:
                # Close connection
                self.ssh.close()
                self.ssh = None
        except Exception as e:
            LOG.error(e)

    def do_exec(self, command_str):
        """Execute command"""
        re = None
        try:
            if command_str is not None:
                self.connect()
                re = self.exec_command(command_str)
        except paramiko.AuthenticationException as ae:
            LOG.error('doexec Authentication error:{}'.format(ae))
            raise exception.InvalidUsernameOrPassword()
        except Exception as e:
            LOG.error('doexec InvalidUsernameOrPassword error:{}'.format(e))
            if 'WSAETIMEDOUT' in str(e):
                raise exception.SSHConnectTimeout()
            elif 'No authentication methods available' in str(e) \
                    or 'Authentication failed' in str(e):
                raise exception.InvalidUsernameOrPassword()
            elif 'not a valid RSA private key file' in str(e):
                raise exception.InvalidPrivateKey()
            elif 'not found in known_hosts' in str(e):
                raise exception.SSHNotFoundKnownHosts(self.ssh_host)
            else:
                raise exception.SSHException()

        finally:
            self.close()
        return re


class SSHPool(pools.Pool):
    SOCKET_TIMEOUT = 10
    MAX_POOL_SIZE = 3

    def __init__(self, **kwargs):
        ssh_access = kwargs.get('ssh')
        if ssh_access is None:
            raise exception.InvalidInput('Input ssh_access is missing')
        self.ssh_host = ssh_access.get('host')
        self.ssh_port = ssh_access.get('port')
        self.ssh_username = ssh_access.get('username')
        self.ssh_password = ssh_access.get('password')
        self.ssh_pub_key_type = ssh_access.get('pub_key_type')
        self.ssh_pub_key = ssh_access.get('pub_key')
        self.ssh_conn_timeout = ssh_access.get('conn_timeout')
        self.conn_timeout = self.SOCKET_TIMEOUT
        if self.ssh_conn_timeout is None:
            self.ssh_conn_timeout = SSHPool.SOCKET_TIMEOUT
        ssh_max_size = kwargs.get('ssh_max_size')
        if ssh_max_size is None:
            ssh_max_size = self.MAX_POOL_SIZE
        super(SSHPool, self).__init__(min_size=0, max_size=ssh_max_size)

    def set_host_key(self, host_key, ssh):
        """
        Set public key,because input kwargs parameter host_key is string,
        not a file path,we can not use load file to get public key,so we set
        it as a string.
        :param str host_key: the public key which as a string
        """
        if (len(host_key) == 0) or (host_key[0] == "#"):
            return
        try:
            e = HostKeyEntry.from_line(host_key)
        except exception.SSHException:
            return
        if e is not None:
            host_names = e.hostnames
            for h in host_names:
                if ssh._host_keys.check(h, e.key):
                    e.hostnames.remove(h)
            if len(e.hostnames):
                ssh._host_keys._entries.append(e)

    def create(self):
        ssh = paramiko.SSHClient()
        try:
            if self.ssh_pub_key is None:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                host_key = '%s %s %s' % \
                           (self.ssh_host, self.ssh_pub_key_type,
                            self.ssh_pub_key)
                self.set_host_key(host_key, ssh)

            ssh.connect(hostname=self.ssh_host, port=self.ssh_port,
                        username=self.ssh_username,
                        password=cryptor.decode(self.ssh_password),
                        timeout=self.ssh_conn_timeout)
            if self.conn_timeout:
                transport = ssh.get_transport()
                transport.set_keepalive(self.SOCKET_TIMEOUT)
            return ssh
        except Exception as e:
            err = six.text_type(e)
            LOG.error('doexec InvalidUsernameOrPassword error')
            if 'timed out' in err:
                raise exception.InvalidIpOrPort()
            elif 'No authentication methods available' in err \
                    or 'Authentication failed' in err:
                raise exception.InvalidUsernameOrPassword()
            elif 'not a valid RSA private key file' in err:
                raise exception.InvalidPrivateKey()
            elif 'not found in known_hosts' in err:
                raise exception.SSHNotFoundKnownHosts(self.ssh_host)
            else:
                raise exception.SSHException(err)

    def get(self):
        """Return an item from the pool, when one is available.

        This may cause the calling greenthread to block. Check if a
        connection is active before returning it. For dead connections
        create and return a new connection.
        """
        if self.free_items:
            conn = self.free_items.popleft()
            if conn:
                if conn.get_transport().is_active():
                    return conn
                else:
                    conn.close()
                    self.current_size -= 1
        if self.current_size < self.max_size:
            try:
                self.current_size += 1
                created = self.create()
            except Exception as e:
                err = six.text_type(e)
                self.current_size -= 1
                raise exception.SSHException(err)
            return created
        return self.channel.get()

    def remove(self, ssh):
        """Close an ssh client and remove it from free_items."""
        ssh.close()
        if ssh in self.free_items:
            self.free_items.remove(ssh)
            if self.current_size > 0:
                self.current_size -= 1

    def put(self, conn):
        if self.current_size > self.max_size:
            conn.close()
            self.current_size -= 1
            return
        super(SSHPool, self).put(conn)

    def do_exec(self, command_str):
        result = ''
        try:
            with self.item() as ssh:
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
            if 'timed out' in err \
                    or 'SSH connect timeout' in err:
                raise exception.SSHConnectTimeout()
            elif 'No authentication methods available' in err \
                    or 'Authentication failed' in err \
                    or 'Invalid username or password' in err:
                raise exception.InvalidUsernameOrPassword()
            elif 'not a valid RSA private key file' in err \
                    or 'not a valid RSA private key' in err:
                raise exception.InvalidPrivateKey()
            else:
                raise exception.SSHException(err)
        return result
