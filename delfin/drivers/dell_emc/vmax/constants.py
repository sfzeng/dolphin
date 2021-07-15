# Copyright 2020 The SODA Authors.
#
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

# minimum interval supported by VMAX
VMAX_PERF_MIN_INTERVAL = 5

ARRAY_METRICS = ["HostIOs",
                 "HostMBWritten",
                 "ReadResponseTime",
                 "HostMBReads",
                 "HostReads",
                 "HostWrites",
                 "WriteResponseTime"
                 ]
VMAX_REST_TARGET_URI_ARRAY_PERF = '/performance/Array/metrics'

VMAX_METRICS = [
    'iops',
    'readIops',
    'writeIops',
    'throughput',
    'readThroughput',
    'writeThroughput',
    'responseTime'
]

BEDIRECTOR_METRICS = {
    'iops': 'IOs',
    'throughput': 'MBs',
    'readThroughput': 'MBRead',
    'writeThroughput': 'MBWritten',
}
FEDIRECTOR_METRICS = {
    'iops': 'HostIOs',
    'throughput': 'HostMBs',
}
RDFDIRECTOR_METRICS = {
    'iops': 'IOs',
    'throughput': 'MBSentAndReceived',
    'readThroughput': 'MBRead',
    'writeThroughput': 'MBWritten',
    'responseTime': 'AverageIOServiceTime',
}
BEPORT_METRICS = {
    'iops': 'IOs',
    'throughput': 'MBs',
    'readThroughput': 'MBRead',
    'writeThroughput': 'MBWritten',
}
FEPORT_METRICS = {
    'iops': 'IOs',
    'throughput': 'MBs',
    'readThroughput': 'MBRead',
    'writeThroughput': 'MBWritten',
    'responseTime': 'ResponseTime',
}
RDFPORT_METRICS = {
    'iops': 'IOs',
    'throughput': 'MBs',
    'readThroughput': 'MBRead',
    'writeThroughput': 'MBWritten',
}
POOL_METRICS = {
    'iops': 'HostIOs',
    'readIops': 'HostReads',
    'writeIops': 'HostWrites',
    'throughput': 'HostMBs',
    'readThroughput': 'HostMBReads',
    'writeThroughput': 'HostMBWritten',
    'responseTime': 'ResponseTime',
}
STORAGE_METRICS = {
    'iops': 'HostIOs',
    'readIops': 'HostReads',
    'writeIops': 'HostWrites',
    'throughput': 'HostMBs',
    'readThroughput': 'HostMBReads',
    'writeThroughput': 'HostMBWritten',
}

IOPS_DESCRIPTION = {
    "unit": "IOPS",
    "description": "Input/output operations per second"
}
READ_IOPS_DESCRIPTION = {
    "unit": "IOPS",
    "description": "Read input/output operations per second"
}
WRITE_IOPS_DESCRIPTION = {
    "unit": "IOPS",
    "description": "Write input/output operations per second"
}
THROUGHPUT_DESCRIPTION = {
    "unit": "MB/s",
    "description": "Represents how much data is "
                   "successfully transferred in MB/s"
}
READ_THROUGHPUT_DESCRIPTION = {
    "unit": "MB/s",
    "description": "Represents how much data read is "
                   "successfully transferred in MB/s"
}
WRITE_THROUGHPUT_DESCRIPTION = {
    "unit": "MB/s",
    "description": "Represents how much data write is "
                   "successfully transferred in MB/s"
}
RESPONSE_TIME_DESCRIPTION = {
    "unit": "ms",
    "description": "Average time taken for an IO "
                   "operation in ms"
}
IO_SIZE_DESCRIPTION = {
    "unit": "KB",
    "description": "The average size of IO requests in KB"
}
READ_IO_SIZE_DESCRIPTION = {
    "unit": "KB",
    "description": "The average size of read IO requests in KB"
}
WRITE_IO_SIZE_DESCRIPTION = {
    "unit": "KB",
    "description": "The average size of write IO requests in KB"
}
STORAGE_CAP = {
    "iops": IOPS_DESCRIPTION,
    "readIops": READ_IOPS_DESCRIPTION,
    "writeIops": WRITE_IOPS_DESCRIPTION,
    "throughput": THROUGHPUT_DESCRIPTION,
    "readThroughput": READ_THROUGHPUT_DESCRIPTION,
    "writeThroughput": WRITE_THROUGHPUT_DESCRIPTION,
    "responseTime": RESPONSE_TIME_DESCRIPTION,
}
POOL_CAP = {
    "iops": IOPS_DESCRIPTION,
    "readIops": READ_IOPS_DESCRIPTION,
    "writeIops": WRITE_IOPS_DESCRIPTION,
    "throughput": THROUGHPUT_DESCRIPTION,
    "readThroughput": READ_THROUGHPUT_DESCRIPTION,
    "writeThroughput": WRITE_THROUGHPUT_DESCRIPTION,
    "responseTime": RESPONSE_TIME_DESCRIPTION,
}
CONTROLLER_CAP = {
    "iops": IOPS_DESCRIPTION,
    "throughput": THROUGHPUT_DESCRIPTION,
    "readThroughput": READ_THROUGHPUT_DESCRIPTION,
    "writeThroughput": WRITE_THROUGHPUT_DESCRIPTION,
    "responseTime": RESPONSE_TIME_DESCRIPTION,
}
PORT_CAP = {
    "iops": IOPS_DESCRIPTION,
    "throughput": THROUGHPUT_DESCRIPTION,
    "readThroughput": READ_THROUGHPUT_DESCRIPTION,
    "writeThroughput": WRITE_THROUGHPUT_DESCRIPTION,
    "responseTime": RESPONSE_TIME_DESCRIPTION,
}
