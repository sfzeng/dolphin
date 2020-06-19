#!/bin/bash
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

curr_dir=$(dirname "$0")
API_PROC_PATH=${curr_dir}/../dolphin/cmd/api.py
ALERT_PROC_PATH=${curr_dir}/../dolphin/cmd/alert.py
TASK_PROC_PATH=${curr_dir}/../dolphin/cmd/alert.py

api_proc_id=$(ps -eaf |grep ${API_PROC_PATH} | grep -v grep |awk '{print $2}')
task_proc_id=$(ps -eaf |grep ${TASK_PROC_PATH} | grep -v grep |awk '{print $2}')
alert_proc_id=$(ps -eaf |grep ${ALERT_PROC_PATH} | grep -v grep |awk '{print $2}')

for i in "${api_proc_id[@]}"
do
    if [ ! $i == "" ]; then
        echo "Killing sim process ${i}"
        $(kill -9 $i)
    fi
done

for i in "${task_proc_id[@]}"
do
    if [ ! $i == "" ]; then
        echo "Killing sim process ${i}"
        $(kill -9 $i)
    fi
done

for i in "${alert_proc_id[@]}"
do
    if [ ! $i == "" ]; then
        echo "Killing sim process ${i}"
        $(kill -9 $i)
    fi
done

$(rm -rf /etc/dolphin)
$(rm -rf /var/lib/dolphin)