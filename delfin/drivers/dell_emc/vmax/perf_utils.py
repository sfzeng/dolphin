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

import time

from collections import Counter

from delfin.drivers.dell_emc.vmax import constants


def epoch_time_ms_now():
    """Get current time in epoch ms.
    :returns: epoch time in milli seconds
     """
    ms = int(time.time() * 1000)
    return ms


def epoch_time_interval_ago(interval_seconds=constants.VMAX_PERF_MIN_INTERVAL):
    """Get epoch time in milliseconds  before an interval
    :param interval_seconds: interval in seconds
    :returns: epoch time in milliseconds
    """
    return int(epoch_time_ms_now() - (interval_seconds * 1000))


def generate_performance_payload(array, start_time, end_time, metrics):
    """Generate request payload for VMAX performance POST request
    :param array: symmetrixID
    :param start_time: start time for collection
    :param end_time: end time for collection
    :param metrics: metrics to be collected
    :returns: payload dictionary
    """
    return {'symmetrixId': str(array),
            "endDate": end_time,
            "startDate": start_time,
            "metrics": metrics,
            "dataFormat": "Average"}


def parse_performance_data(response):
    """Parse metrics response to a map
    :param response: response from unispshere REST API
    :returns: map with key as metric name and value as dictionary
        containing {timestamp: value} for a the timestamps available
    """
    metrics_map = {}
    for metrics in response["resultList"]["result"]:
        timestamp = metrics["timestamp"]
        for key, value in metrics.items():
            metrics_map[key] = metrics_map.get(key, {})
            metrics_map[key][timestamp] = value
    return metrics_map


def construct_metrics(metrics_map, storage_id, perf):
    metrics_list = []
    for key in constants.VMAX_METRICS:
        delfin_metrics = metrics_map.get(key)
        if not delfin_metrics:
            continue
        labels = {
            'storage_id': storage_id,
            'resource_type': 'controller',
            'resource_id': perf.get('resource_id'),
            'resource_name': perf.get('resource_name'),
            'type': 'RAW',
            'unit': constants.CONTROLLER_CAP[key]['unit']
        }
        delfin_metrics = metrics_map[key]
        metrics = constants.metric_struct(name=key, labels=labels,
                                          values=delfin_metrics)
        metrics_list.append(metrics)
    return metrics_list


def map_array_perf_metrics_to_delfin_metrics(metrics_value_map):
    """map vmax array performance metrics values  to delfin metrics values
        :param metrics_value_map: metric to values map of vmax metrics
        :returns: map with key as delfin metric name and value as dictionary
            containing {timestamp: value} for a the timestamps available
        """
    # read and write response_time
    read_response_values_dict = metrics_value_map.get('ReadResponseTime')
    write_response_values_dict = metrics_value_map.get('WriteResponseTime')
    if read_response_values_dict or write_response_values_dict:
        response_time_values_dict = \
            Counter(read_response_values_dict) + \
            Counter(write_response_values_dict)
    # bandwidth metrics
    read_bandwidth_values_dict = metrics_value_map.get('HostMBReads')
    write_bandwidth_values_dict = metrics_value_map.get('HostMBWritten')
    if read_bandwidth_values_dict or write_bandwidth_values_dict:
        bandwidth_values_dict = \
            Counter(read_bandwidth_values_dict) +\
            Counter(write_bandwidth_values_dict)
    throughput_values_dict = metrics_value_map.get('HostIOs')
    read_throughput_values_dict = metrics_value_map.get('HostReads')
    write_throughput_values_dict = metrics_value_map.get('HostWrites')
    # map values to delfin metrics spec
    delfin_metrics = {'responseTime': response_time_values_dict,
                      'readThroughput': read_bandwidth_values_dict,
                      'writeThroughput': write_bandwidth_values_dict,
                      'requests': throughput_values_dict,
                      'readRequests': read_throughput_values_dict,
                      'writeRequests': write_throughput_values_dict,
                      'throughput': bandwidth_values_dict}
    return delfin_metrics
