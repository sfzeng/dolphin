# Copyright 2021 The SODA Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import time

import six
from oslo_log import log

from delfin import exception
from delfin.common import alert_util
from delfin.common import constants

LOG = log.getLogger(__name__)


class AlertHandler(object):

    TIME_PATTERN = "%Y-%m-%dT%H:%M:%S%z"

    ALERT_LEVEL_MAP = {'error': constants.Severity.CRITICAL,
                       'warning': constants.Severity.WARNING,
                       'info': constants.Severity.INFORMATIONAL
                       }
    SECONDS_TO_MS = 1000

    def parse_queried_alerts(self, alert_model_list, alert_list, query_para):
        alerts = alert_list.get('data', {}).get('events')
        for alert in alerts:
            try:
                occur_time = int(time.mktime(time.strptime(
                    alert.get('time'),
                    self.TIME_PATTERN)))
                if not alert_util.is_alert_in_time_range(
                        query_para, int(occur_time *
                                        AlertHandler.SECONDS_TO_MS)):
                    continue

                alert_model = {}
                location = ''
                resource_type = constants.DEFAULT_RESOURCE_TYPE
                alert_model['alert_id'] = alert.get('type')
                alert_model['alert_name'] = alert.get('description')
                alert_model['severity'] = self.ALERT_LEVEL_MAP.get(
                    alert.get('severity'),
                    constants.Severity.INFORMATIONAL)
                alert_model['description'] = alert.get('formatted_parameter')
                alert_model['category'] = constants.Category.FAULT
                alert_model['type'] = constants.EventType.EQUIPMENT_ALARM
                alert_model['sequence_number'] = alert.get('id')
                alert_model['occur_time'] = int(occur_time *
                                                AlertHandler.SECONDS_TO_MS)
                alert_model['resource_type'] = resource_type
                alert_model['location'] = location
                alert_model_list.append(alert_model)
            except Exception as e:
                LOG.error(e)
                err_msg = "Failed to build alert model as some attributes " \
                          "missing in queried alerts: %s" % (six.text_type(e))
                raise exception.InvalidResults(err_msg)
