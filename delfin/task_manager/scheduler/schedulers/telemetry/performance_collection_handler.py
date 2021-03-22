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

from datetime import datetime

import six
from oslo_log import log

from delfin import db
from delfin import exception
from delfin.common.constants import TelemetryCollection
from delfin.db.sqlalchemy.models import FailedTask
from delfin.task_manager import rpcapi as task_rpcapi
from delfin.task_manager.scheduler.schedulers.telemetry. \
    failed_performance_collection_handler import \
    FailedPerformanceCollectionHandler
from delfin.task_manager.tasks import telemetry

LOG = log.getLogger(__name__)


class PerformanceCollectionHandler(object):
    def __init__(self, ctx, task_id, storage_id, args, interval):
        self.ctx = ctx
        self.task_id = task_id
        self.storage_id = storage_id
        self.args = args
        self.interval = interval
        self.task_rpcapi = task_rpcapi.TaskAPI()

    @staticmethod
    def get_instance(ctx, task_id):
        task = db.task_get(ctx, task_id)
        return PerformanceCollectionHandler(ctx, task_id, task['storage_id'],
                                            task['args'], task['interval'])

    def __call__(self):
        # Handles performance collection from driver and dispatch
        start_time = None
        end_time = None
        try:
            LOG.debug('Collecting performance metrics for task id: %s'
                      % self.task_id)
            current_time = int(datetime.utcnow().timestamp())

            # Times are epoch time in milliseconds
            end_time = current_time * 1000
            start_time = end_time - (self.interval * 1000)
            status = self.task_rpcapi. \
                collect_telemetry(self.ctx, self.storage_id,
                                  telemetry.TelemetryTask.__module__ + '.' +
                                  'PerformanceCollectionTask', self.args,
                                  start_time, end_time)

            db.task_update(self.ctx, self.task_id,
                           {'last_run_time': current_time})

            if not status:
                raise exception.TelemetryTaskExecError()
        except Exception as e:
            LOG.error("Failed to collect performance metrics for "
                      "task id :{0}, reason:{1}".format(self.task_id,
                                                        six.text_type(e)))
            self._handle_task_failure(start_time, end_time)
        else:
            LOG.debug("Performance collection done for storage id :{0}"
                      ",task id :{1} and interval(in sec):{2}"
                      .format(self.storage_id, self.task_id, self.interval))

    def _handle_task_failure(self, start_time, end_time):
        failed_task = {FailedTask.task_id.name: self.task_id,
                       FailedTask.interval.name:
                           TelemetryCollection.PERIODIC_JOB_SCHEDULE_INTERVAL,
                       FailedTask.end_time.name: end_time,
                       FailedTask.start_time.name: start_time,
                       FailedTask.method.name:
                           FailedPerformanceCollectionHandler.__module__ +
                           '.' + FailedPerformanceCollectionHandler.__name__,
                       FailedTask.retry_count.name: 0}
        db.failed_task_create(self.ctx, failed_task)
