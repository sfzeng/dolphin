# Copyright 2020 The SODA Authors.
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

import six
import abc


@six.add_metaclass(abc.ABCMeta)
class StorageDriver(object):

    def __init__(self, **kwargs):
        """
        :param kwargs:  A dictionary, include access information. Pay
            attention that it's not safe to save username and password
            in memory, so suggest each driver use them to get session
            instead of save them in memory directly.
        """
        self.storage_id = kwargs.get('storage_id', None)

    @abc.abstractmethod
    def reset_connection(self, context, **kwargs):
        """ Reset connection with backend with new args """
        pass

    @abc.abstractmethod
    def get_storage(self, context):
        """Get storage device information from storage system"""
        pass

    def get_centralized_manager(self, context):
        """Get storage device information from storage system"""
        pass

    @abc.abstractmethod
    def list_storage_pools(self, context):
        """List all storage pools from storage system."""
        pass

    @abc.abstractmethod
    def list_volumes(self, context):
        """List all storage volumes from storage system."""
        pass

    @abc.abstractmethod
    def list_controllers(self, context):
        """List all storage controllers from storage system."""
        pass

    @abc.abstractmethod
    def list_ports(self, context):
        """List all ports from storage system."""
        pass

    @abc.abstractmethod
    def list_disks(self, context):
        """List all disks from storage system."""
        pass

    @abc.abstractmethod
    def add_trap_config(self, context, trap_config):
        """Config the trap receiver in storage system."""
        pass

    @abc.abstractmethod
    def remove_trap_config(self, context, trap_config):
        """Remove trap receiver configuration from storage system."""
        pass

    @staticmethod
    def parse_alert(context, alert):
        """Parse alert data got from snmp trap server."""

        """
        Alert Model	Description
        *****Filled from driver side ***********************
        alert_id	Unique identification for a given alert type
        alert_name	Unique name for a given alert type
        severity	Severity of the alert
        category	Category of alert generated
        type	Type of the alert generated
        sequence_number	Sequence number for the alert, uniquely identifies a
                                  given alert instance used for
                                  clearing the alert
        occur_time	Time at which alert is generated from device in epoch
                    format
        description	Possible cause description or other details about
                                the alert
        recovery_advice	Some suggestion for handling the given alert
        resource_type	Resource type of device/source generating alert
        location	Detailed info about the tracing the alerting device such as
                    slot, rack, component, parts etc
        *****************************************************
        """

        pass

    @abc.abstractmethod
    def list_alerts(self, context, query_para=None):
        """List all current alerts from storage system."""
        """
        query_para is an optional para which contains 'begin_time' and
        'end_time' (in milliseconds) which is to be used to filter
        alerts at driver
        """
        pass

    @abc.abstractmethod
    def clear_alert(self, context, sequence_number):
        """Clear alert from storage system."""
        pass

    def collect_perf_metrics(self, context, storage_id,
                             resource_metrics, start_time, end_time):
        """Collect performance metrics from storage system."""

        """
        Input:
        context: context information
        storage_id: storage identifier
        resource_metrics: dictionary represents the collection configuration
        Example:
        resource_metrics =
              {'storagePool':
                        ['readThroughput', 'writeThroughput', 'responseTime'],
                'volume':
                        ['readThroughput', 'writeThroughput']}
        start_time	Time from which the performance metric to be collected
                    It is in epoch format in milliseconds
        end_time	Time until which the performance metric to be collected
                    It is in epoch format in milliseconds

        Response: List of metric with details
                Format : [[Metric(name=metric_1,
                             labels={'key_1': value_1,
                                     'key_2': value_2,},
                             values={timestamp_0: value_0,
                                     timestamp_n: value_n,})]
        Example:
        [[Metric(name='responseTime',
                     labels={'storage_id': '1f8d6982-2ac2-4fa9-95ef-78f359de',
                             'resource_type': 'storagePool'},
                     values={1616560337249: 96.12081735538251}),
          Metric(name='throughput',
                     labels={'storage_id': '1f8d6982-2ac2-4fa9-95ef-78f359de',
                             'resource_type': 'storagePool'},
                     values={1616560337249: 90.08194398331271})]
        """
        pass

    def list_quotas(self, context):
        """List all quotas from storage system."""
        raise NotImplementedError(
            "Driver API list_quotas() is not Implemented")

    def list_filesystems(self, context):
        """List all filesystems from storage system."""
        raise NotImplementedError(
            "Driver API list_filesystems() is not Implemented")

    def list_qtrees(self, context):
        """List all qtrees from storage system."""
        raise NotImplementedError(
            "Driver API list_qtrees() is not Implemented")

    def list_shares(self, context):
        """List all shares from storage system."""
        raise NotImplementedError(
            "Driver API list_shares() is not Implemented")

    @staticmethod
    def get_capabilities(context):
        """Get capability of driver"""
        pass
