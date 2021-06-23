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

from oslo_log import log
from oslo_utils import units

from delfin import exception
from delfin.common import constants
from delfin.drivers.dell_emc.vmax import rest, perf_utils

LOG = log.getLogger(__name__)

EMBEDDED_UNISPHERE_ARRAY_COUNT = 1


class VMAXClient(object):
    """ Client class for communicating with VMAX storage """

    def __init__(self, **kwargs):
        self.uni_version = None
        self.array_id = None
        rest_access = kwargs.get('rest')
        if rest_access is None:
            raise exception.InvalidInput('Input rest_access is missing')
        self.rest = rest.VMaxRest()
        self.rest.set_rest_credentials(rest_access)
        self.reset_connection(**kwargs)

    def reset_connection(self, **kwargs):
        """ Reset connection to VMAX storage with new configs """
        self.rest.verify = kwargs.get('verify', False)
        self.rest.establish_rest_session()

    def init_connection(self, access_info):
        """ Given the access_info get a connection to VMAX storage """
        try:
            ver, self.uni_version = self.rest.get_uni_version()
            LOG.info('Connected to Unisphere Version: {0}'.format(ver))
        except exception.InvalidUsernameOrPassword as e:
            msg = "Failed to connect VMAX. Reason: {}".format(e.msg)
            LOG.error(msg)
            raise e
        except (exception.SSLCertificateFailed,
                exception.SSLHandshakeFailed) as e:
            msg = ("Failed to connect to VMAX: {}".format(e))
            LOG.error(msg)
            raise
        except Exception as err:
            msg = ("Failed to connect to VMAX. Host or Port is not correct: "
                   "{}".format(err))
            LOG.error(msg)
            raise exception.InvalidIpOrPort()

        if not self.uni_version:
            msg = "Invalid input. Failed to get vmax unisphere version"
            raise exception.InvalidInput(msg)

        self.array_id = access_info.get('extra_attributes', {}). \
            get('array_id', None)

        try:
            # Get array details from unisphere
            array = self.rest.get_array_detail(version=self.uni_version)
            if not array:
                msg = "Failed to get array details"
                raise exception.InvalidInput(msg)

            if len(array['symmetrixId']) == EMBEDDED_UNISPHERE_ARRAY_COUNT:
                if not self.array_id:
                    self.array_id = array['symmetrixId'][0]
                elif self.array_id != array['symmetrixId'][0]:
                    msg = "Invalid array_id. Expected id: {}". \
                        format(array['symmetrixId'])
                    raise exception.InvalidInput(msg)
        except exception.SSLCertificateFailed:
            LOG.error('SSL certificate failed when init connection for VMax')
            raise
        except Exception as err:
            msg = "Failed to get array details from VMAX: {}".format(err)
            raise exception.StorageBackendException(msg)

        if not self.array_id:
            msg = "Input array_id is missing. Supported ids: {}". \
                format(array['symmetrixId'])
            raise exception.InvalidInput(msg)

    def get_array_details(self):
        try:
            # Get the VMAX array properties
            return self.rest.get_vmax_array_details(version=self.uni_version,
                                                    array=self.array_id)
        except exception.SSLCertificateFailed:
            LOG.error('SSL certificate failed when get array info for VMax')
            raise
        except Exception as err:
            msg = "Failed to get array details from VMAX: {}".format(err)
            LOG.error(msg)
            raise exception.StorageBackendException(msg)

    def get_storage_capacity(self):
        try:
            storage_info = self.rest.get_system_capacity(
                self.array_id, self.uni_version)

            total_capacity = 0
            used_capacity = 0
            free_capacity = 0
            raw_capacity = 0
            subscribed_capacity = 0
            if int(self.uni_version) < 90:
                physical_capacity = storage_info.get('physicalCapacity')
                total_cap = storage_info.get('total_usable_cap_gb')
                used_cap = storage_info.get('total_allocated_cap_gb')
                subscribed_cap = storage_info.get('total_subscribed_cap_gb')
                total_raw = physical_capacity.get('total_capacity_gb')
                free_cap = total_cap - used_cap

                total_capacity = int(total_cap * units.Gi)
                used_capacity = int(used_cap * units.Gi)
                free_capacity = int(free_cap * units.Gi)
                raw_capacity = int(total_raw * units.Gi)
                subscribed_capacity = int(subscribed_cap * units.Gi)

            else:
                system_capacity = storage_info['system_capacity']
                physical_capacity = storage_info.get('physicalCapacity')
                total_cap = system_capacity.get('usable_total_tb')
                used_cap = system_capacity.get('usable_used_tb')
                subscribed_cap = system_capacity.get('subscribed_total_tb')
                total_raw = physical_capacity.get('total_capacity_gb')
                free_cap = total_cap - used_cap

                total_capacity = int(total_cap * units.Ti)
                used_capacity = int(used_cap * units.Ti)
                free_capacity = int(free_cap * units.Ti)
                raw_capacity = int(total_raw * units.Gi)
                subscribed_capacity = int(subscribed_cap * units.Ti)

            return total_capacity, used_capacity, free_capacity,\
                raw_capacity, subscribed_capacity

        except exception.SSLCertificateFailed:
            LOG.error('SSL certificate failed when '
                      'get storage capacity for VMax')
            raise
        except Exception as err:
            msg = "Failed to get capacity from VMAX: {}".format(err)
            LOG.error(msg)
            raise exception.StorageBackendException(msg)

    def list_storage_pools(self, storage_id):

        try:
            # Get list of SRP pool names
            pools = self.rest.get_srp_by_name(
                self.array_id, self.uni_version, srp='')['srpId']

            pool_list = []
            for pool in pools:
                pool_info = self.rest.get_srp_by_name(
                    self.array_id, self.uni_version, srp=pool)

                total_cap = 0
                used_cap = 0
                subscribed_cap = 0
                if int(self.uni_version) < 90:
                    total_cap = pool_info['total_usable_cap_gb'] * units.Gi
                    used_cap = pool_info['total_allocated_cap_gb'] * units.Gi
                    subscribed_cap = \
                        pool_info['total_subscribed_cap_gb'] * units.Gi
                else:
                    srp_cap = pool_info['srp_capacity']
                    total_cap = srp_cap['usable_total_tb'] * units.Ti
                    used_cap = srp_cap['usable_used_tb'] * units.Ti
                    subscribed_cap = srp_cap['subscribed_total_tb'] * units.Ti

                p = {
                    "name": pool,
                    "storage_id": storage_id,
                    "native_storage_pool_id": pool_info["srpId"],
                    "description": "Dell EMC VMAX Pool",
                    "status": constants.StoragePoolStatus.NORMAL,
                    "storage_type": constants.StorageType.BLOCK,
                    "total_capacity": int(total_cap),
                    "used_capacity": int(used_cap),
                    "free_capacity": int(total_cap - used_cap),
                    "subscribed_capacity": int(subscribed_cap),
                }

                pool_list.append(p)

            return pool_list

        except exception.SSLCertificateFailed:
            LOG.error('SSL certificate failed when list pools for VMax')
            raise
        except Exception as err:
            msg = "Failed to get pool metrics from VMAX: {}".format(err)
            LOG.error(msg)
            raise exception.StorageBackendException(msg)

    def list_volumes(self, storage_id):

        try:
            # Get default SRPs assigned for the array
            default_srps = self.rest.get_default_srps(
                self.array_id, version=self.uni_version)
            # List all volumes except data volumes
            volumes = self.rest.get_volume_list(
                self.array_id, version=self.uni_version,
                params={'data_volume': 'false'})

            # TODO: Update constants.VolumeStatus to make mapping more precise
            switcher = {
                'Ready': constants.VolumeStatus.AVAILABLE,
                'Not Ready': constants.VolumeStatus.AVAILABLE,
                'Mixed': constants.VolumeStatus.AVAILABLE,
                'Write Disabled': constants.VolumeStatus.AVAILABLE,
                'N/A': constants.VolumeStatus.ERROR,
            }

            volume_list = []
            for volume in volumes:
                # Get volume details
                vol = self.rest.get_volume(self.array_id,
                                           self.uni_version, volume)

                emulation_type = vol['emulation']
                total_cap = vol['cap_mb'] * units.Mi
                used_cap = (total_cap * vol['allocated_percent']) / 100.0
                free_cap = total_cap - used_cap

                status = switcher.get(vol.get('status'),
                                      constants.VolumeStatus.ERROR)

                description = "Dell EMC VMAX volume"
                if vol['type'] == 'TDEV':
                    description = "Dell EMC VMAX 'thin device' volume"

                name = volume
                if vol.get('volume_identifier'):
                    name = volume + ':' + vol['volume_identifier']

                v = {
                    "name": name,
                    "storage_id": storage_id,
                    "description": description,
                    "status": status,
                    "native_volume_id": vol['volumeId'],
                    "wwn": vol['wwn'],
                    "type": constants.VolumeType.THIN,
                    "total_capacity": int(total_cap),
                    "used_capacity": int(used_cap),
                    "free_capacity": int(free_cap),
                }

                if vol['num_of_storage_groups'] == 1:
                    sg = vol['storageGroupId'][0]
                    sg_info = self.rest.get_storage_group(
                        self.array_id, self.uni_version, sg)
                    v['native_storage_pool_id'] = \
                        sg_info.get('srp', default_srps[emulation_type])
                    v['compressed'] = sg_info.get('compression', False)
                else:
                    v['native_storage_pool_id'] = default_srps[emulation_type]

                volume_list.append(v)

            return volume_list

        except exception.SSLCertificateFailed:
            LOG.error('SSL certificate failed when list volumes for VMax')
            raise
        except Exception as err:
            msg = "Failed to get list volumes from VMAX: {}".format(err)
            LOG.error(msg)
            raise exception.StorageBackendException(msg)

    def list_controllers(self, storage_id):
        try:
            # Get list of Directors
            directors = self.rest.get_director_list(self.array_id,
                                                    self.uni_version)
            controller_list = []
            for director in directors:
                director_info = self.rest.get_director(
                    self.array_id, self.uni_version, director)

                status = constants.ControllerStatus.NORMAL
                if director_info.get('availability', '').upper() != 'ONLINE':
                    status = constants.ControllerStatus.OFFLINE

                controller = {
                    'name': 'director_'
                            + str(director_info.get('director_number')),
                    'storage_id': storage_id,
                    'native_controller_id': director_info['directorId'],
                    'status': status,
                    'location':
                        'slot_' +
                        str(director_info.get('director_slot_number')),
                    'soft_version': None,
                    'cpu_info': 'number_of_cores_'
                                + str(director_info.get('num_of_cores')),
                    'memory_size': None

                }
                controller_list.append(controller)
            return controller_list

        except exception.SSLCertificateFailed:
            LOG.error('SSL certificate failed when list pools for VMax')
            raise
        except Exception as err:
            msg = "Failed to get controller metrics from VMAX: {}".format(err)
            LOG.error(msg)
            raise exception.ControllerNotFound(self.array_id)

    def list_ports(self, storage_id):
        try:
            # Get list of Directors
            directors = self.rest.get_director_list(self.array_id,
                                                    self.uni_version)
            port_list = []
            for director in directors:
                port_keys = self.rest.get_port_list(
                    self.array_id, self.uni_version, director)
                for port_key in port_keys:
                    port_info = self.rest.get_port(
                        self.array_id, self.uni_version,
                        director, port_key['portId'])['symmetrixPort']

                    connection_status = \
                        constants.PortConnectionStatus.CONNECTED
                    if port_info.get('port_status',
                                     '').upper().find('OFF') != -1:
                        connection_status = \
                            constants.PortConnectionStatus.DISCONNECTED

                    port_type = constants.PortType.OTHER
                    if port_info.get('type', '').upper().find('FIBRE') != -1:
                        port_type = constants.PortType.FC
                    if port_info.get('type', '').upper().find('ETH') != -1:
                        port_type = constants.PortType.ETH

                    name = "{0}:{1}".format(port_key['directorId'],
                                            port_key['portId'])
                    speed = int(port_info.get('negotiated_speed', '0')) * units.Gi
                    max_speed = int(port_info.get('max_speed', '0')) * units.Gi
                    port_dict = {
                        'name': name,
                        'storage_id': storage_id,
                        'native_port_id': port_key['portId'],
                        'location': 'director_' + port_key['directorId'],
                        'connection_status': connection_status,
                        'health_status': constants.PortHealthStatus.NORMAL,
                        'type': port_type,
                        'logical_type': None,
                        'speed': speed,
                        'max_speed': max_speed,
                        'native_parent_id': port_key['directorId'],
                        'wwn': port_info.get('identifier', None),
                        'mac_address': None,
                        'ipv4': port_info.get('ipv4_address'),
                        'ipv4_mask': port_info.get('ipv4_netmask'),
                        'ipv6': port_info.get('ipv6_address'),
                        'ipv6_mask': None,
                    }
                    port_list.append(port_dict)
            return port_list

        except exception.SSLCertificateFailed:
            LOG.error('SSL certificate failed when list pools for VMax')
            raise
        except Exception as err:
            msg = "Failed to get port metrics from VMAX: {}".format(err)
            LOG.error(msg)
            raise exception.PortNotFound(self.array_id)

    def list_alerts(self, query_para):
        """Get all alerts from an array."""
        return self.rest.get_alerts(query_para, version=self.uni_version,
                                    array=self.array_id)

    def clear_alert(self, sequence_number):
        """Clear alert for given sequence number."""
        return self.rest.clear_alert(sequence_number, version=self.uni_version,
                                     array=self.array_id)

    def get_array_metrics(self, storage_id, start_time, end_time):
        """Get performance metrics."""
        try:
            # Fetch VMAX Array Performance data from REST client
            # TODO  :
            #  Check whether array is registered for performance collection
            #  in unisphere
            perf_data = self.rest.get_array_metrics(
                self.array_id, start_time, end_time)
            # parse VMAX REST response to metric->values map
            metrics_value_map = perf_utils.parse_performance_data(perf_data)
            # prepare  labels required for array_leval performance data
            labels = {'storage_id': storage_id, 'resource_type': 'array'}
            # map to unified delifn  metrics
            delfin_metrics = perf_utils. \
                map_array_perf_metrics_to_delfin_metrics(metrics_value_map)
            metrics_array = []
            for key in constants.DELFIN_ARRAY_METRICS:
                m = constants.metric_struct(name=key, labels=labels,
                                            values=delfin_metrics[key])
                metrics_array.append(m)
            return metrics_array
        except Exception as err:
            msg = "Failed to get performance metrics data for VMAX: {}".format(
                err)
            LOG.error(msg)
            raise exception.StorageBackendException(msg)

    def get_storage_metrics(self, storage_id, metrics, start_time, end_time):
        """Get performance metrics."""
        print('--JVP--: IN client get_storage_metrics')
        try:
            perf_list = self.rest.get_storage_metrics(
                self.array_id, metrics, start_time, end_time)

            metrics_array = []
            for perf in perf_list:
                metrics_map = perf_utils.parse_performance_data(
                    perf.get('metrics'))
                metrics_list = perf_utils.construct_metrics(
                    metrics_map, storage_id, perf)
                metrics_array.extend(metrics_list)
            return metrics_array
        except Exception as err:
            msg = "Failed to get STORAGE metrics for VMAX: {}".format(
                err)
            LOG.error(msg)
            raise exception.InvalidResults(msg)

    def get_pool_metrics(self, storage_id, metrics, start_time, end_time):
        """Get performance metrics."""

        try:
            perf_list = self.rest.get_pool_metrics(
                self.array_id, metrics, start_time, end_time)

            metrics_array = []
            for perf in perf_list:
                metrics_map = perf_utils.parse_performance_data(
                    perf.get('metrics'))
                metrics_list = perf_utils.construct_metrics(
                    metrics_map, storage_id, perf)
                metrics_array.extend(metrics_list)
            return metrics_array
        except Exception as err:
            msg = "Failed to get STORAGE POOL metrics for VMAX: {}".format(
                err)
            LOG.error(msg)
            raise exception.InvalidResults(msg)

    def get_port_metrics(self, storage_id, metrics, start_time, end_time):
        """Get performance metrics."""

        try:
            perf_list = self.rest.get_port_metrics(
                self.array_id, metrics, start_time, end_time)

            metrics_array = []
            for perf in perf_list:
                metrics_map = perf_utils.parse_performance_data(
                    perf.get('metrics'))
                metrics_list = perf_utils.construct_metrics(
                    metrics_map, storage_id, perf)
                metrics_array.extend(metrics_list)
            return metrics_array
        except Exception as err:
            msg = "Failed to get PORT metrics for VMAX: {}".format(
                err)
            LOG.error(msg)
            raise exception.InvalidResults(msg)

    def get_controller_metrics(self, storage_id,
                               metrics, start_time, end_time):
        """Get performance metrics."""

        try:
            perf_list = self.rest.get_controller_metrics(
                self.array_id, metrics, start_time, end_time)

            metrics_array = []
            for perf in perf_list:
                metrics_map = perf_utils.parse_performance_data(
                    perf.get('metrics'))
                metrics_list = perf_utils.construct_metrics(
                    metrics_map, storage_id, perf)
                metrics_array.extend(metrics_list)
            return metrics_array
        except Exception as err:
            msg = "Failed to get CONTROLLER metrics for VMAX: {}".format(
                err)
            LOG.error(msg)
            raise exception.InvalidResults(msg)
