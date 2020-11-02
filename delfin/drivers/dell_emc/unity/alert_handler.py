# Copyright 2020 The SODA Authors.
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

from oslo_log import log

from delfin import exception
from delfin.common import alert_util
from delfin.common import constants
from delfin.i18n import _

LOG = log.getLogger(__name__)


class AlertHandler(object):

    TIME_PATTERN = "%Y-%m-%d,%H:%M:%S.%fZ"

    OID_SEVERITY = '1.3.6.1.6.3.1.1.4.1'
    OID_NODE = '1.3.6.1.4.1.1139.103.1.18.1.1'
    OID_SYMPTOMID = '1.3.6.1.4.1.1139.103.1.18.1.3'
    OID_TIMESTAMP = '1.3.6.1.4.1.1139.103.1.18.1.5'
    OID_SYMPTOMTEXT = '1.3.6.1.4.1.1139.103.1.18.1.4'
    OID_COMPONENT = '1.3.6.1.4.1.1139.103.1.18.1.2'

    ALERT_LEVEL_MAP = {0: constants.Severity.CRITICAL,
                       1: constants.Severity.CRITICAL,
                       2: constants.Severity.CRITICAL,
                       3: constants.Severity.MAJOR,
                       4: constants.Severity.WARNING,
                       5: constants.Severity.FATAL,
                       6: constants.Severity.INFORMATIONAL,
                       7: constants.Severity.NOT_SPECIFIED
                       }

    TRAP_LEVEL_MAP = {'1.3.6.1.4.1.1139.103.1.18.2.0':
                      constants.Severity.CRITICAL,
                      '1.3.6.1.4.1.1139.103.1.18.2.1':
                      constants.Severity.CRITICAL,
                      '1.3.6.1.4.1.1139.103.1.18.2.2':
                      constants.Severity.CRITICAL,
                      '1.3.6.1.4.1.1139.103.1.18.2.3':
                      constants.Severity.MAJOR,
                      '1.3.6.1.4.1.1139.103.1.18.2.4':
                      constants.Severity.WARNING,
                      '1.3.6.1.4.1.1139.103.1.18.2.5':
                      constants.Severity.FATAL,
                      '1.3.6.1.4.1.1139.103.1.18.2.6':
                      constants.Severity.INFORMATIONAL,
                      '1.3.6.1.4.1.1139.103.1.18.2.7':
                      constants.Severity.NOT_SPECIFIED
                      }

    _mandatory_alert_attributes = (
        OID_SEVERITY,
        OID_NODE,
        OID_SYMPTOMID,
        OID_TIMESTAMP,
        OID_SYMPTOMTEXT,
        OID_COMPONENT,
        OID_COMPONENT
    )

    def parse_alert(self, context, alert):
        for attr in self._mandatory_alert_attributes:
            if not alert.get(attr):
                msg = "Mandatory information %s missing in alert message. " \
                      % attr
                raise exception.InvalidInput(msg)

        try:
            alert_model = dict()
            alert_model['alert_id'] = alert.get(AlertHandler.OID_SYMPTOMID)
            alert_model['alert_name'] = alert.get(AlertHandler.OID_SYMPTOMID)
            alert_model['severity'] = self.TRAP_LEVEL_MAP.get(
                alert.get(AlertHandler.OID_SEVERITY),
                constants.Severity.NOT_SPECIFIED)
            alert_model['category'] = 'Event'
            alert_model['type'] = constants.EventType.EQUIPMENT_ALARM
            alert_model['sequence_number'] \
                = alert.get(AlertHandler.OID_NODE)
            occur_time = alert.get(AlertHandler.OID_TIMESTAMP)
            alert_model['occur_time'] = int(occur_time.timestamp() * 1000)
            alert_model['description'] = alert.get(AlertHandler.OID_COMPONENT)
            alert_model['resource_type'] = constants.DEFAULT_RESOURCE_TYPE
            alert_model['location'] = alert.get(AlertHandler.OID_NODE)

            return alert_model
        except Exception as e:
            LOG.error(e)
            msg = (_("Failed to build alert model as some attributes missing "
                     "in alert message."))
            raise exception.InvalidResults(msg)

    def parse_queried_alerts(self, alert_list, query_para):
        alert_model_list = []
        alerts = alert_list.get('entries')
        for alert in alerts:
            try:
                occur_time = int(time.mktime(time.strptime(
                    alert.get('content').get('timestamp'),
                    self.TIME_PATTERN)))
                if not alert_util.is_alert_in_time_range(query_para,
                                                         occur_time):
                    continue

                alert_model = dict()
                location = ''
                resource_type = constants.DEFAULT_RESOURCE_TYPE
                if 'component' in alert:
                    resource_type = alert.get(
                        'content').get('component').get('resource')
                    location = alert.get(
                        'content').get('component').get('id')

                alert_model['alert_id'] = alert.get(
                    'content').get('messageId')
                alert_model['alert_name'] = alert.get(
                    'content').get('message')
                alert_model['severity'] = self.ALERT_LEVEL_MAP.get(
                    alert.get('content').get('severity'),
                    constants.Severity.NOT_SPECIFIED)
                alert_model['category'] = 'Fault'
                alert_model['type'] = constants.EventType.EQUIPMENT_ALARM
                alert_model['sequence_number'] = alert.get('content').get('id')
                alert_model['occur_time'] = int(occur_time * 1000)
                alert_model['description'] = alert.get('content').get(
                    'description')
                alert_model['resource_type'] = resource_type
                alert_model['location'] = location

                alert_model_list.append(alert_model)
            except Exception as e:
                LOG.error(e)
                msg = (_("Failed to build alert model as some attributes"
                         " missing in queried alerts."))
                raise exception.InvalidResults(msg)
        return alert_model_list

    def add_trap_config(self, context, storage_id, trap_config):
        """Config the trap receiver in storage system."""
        # Currently not implemented
        pass

    def remove_trap_config(self, context, storage_id, trap_config):
        """Remove trap receiver configuration from storage system."""
        # Currently not implemented
        pass

    def clear_alert(self, context, storage_id, alert):
        """Clear alert from storage system."""
        pass
