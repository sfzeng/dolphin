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

from delfin import cryptor
from delfin import db
from delfin import exception
from delfin.common import constants
from delfin.i18n import _

LOG = log.getLogger(__name__)


def encrypt_password(context, access_info):
    for access in constants.ACCESS_TYPE:
        if access_info.get(access):
            access_info[access]['password'] = cryptor.encode(
                access_info[access]['password'])


def check_storage_repetition(context, storage):
    if not storage:
        raise exception.StorageBackendNotFound()

    if not storage.get('serial_number'):
        msg = _("Serial number should be provided by storage.")
        raise exception.InvalidResults(msg)

    filters = dict(serial_number=storage['serial_number'])
    storage_list = db.storage_get_all(context, filters=filters)
    if storage_list:
        msg = (_("Failed to register storage. Reason: same serial number: "
                 "%s detected.") % storage['serial_number'])
        LOG.error(msg)
        raise exception.StorageAlreadyExists()


def check_cm_repetition(context, cm):
    if not cm:
        raise exception.CentralizedManagerNotFound()

    if not cm.get('serial_number'):
        msg = _("serial_number should be provided by CM.")
        raise exception.InvalidResults(msg)

    filters = dict(serial_number=cm['serial_number'])
    cm_list = db.centralized_manager_get_all(context, filters=filters)
    if cm_list:
        msg = (_("Failed to register CM. Reason: same serial_number: "
                 "%s detected.") % cm['serial_number'])
        LOG.error(msg)
        raise exception.CentralizedManagerAlreadyExists()


def check_storage_consistency(context, storage_id, storage_new):
    """Check storage response returned by driver whether it matches the
    storage stored in database.

    :param context: The context of delfin.
    :type context: delfin.context.RequestContext
    :param storage_id: The uuid of storage in database.
    :type storage_id: string
    :param storage_new: The storage response returned by driver.
    :type storage_new: dict
    """
    if not storage_new:
        raise exception.StorageBackendNotFound()

    if not storage_new.get('serial_number'):
        msg = _("Serial number should be provided by storage.")
        raise exception.InvalidResults(msg)

    storage_present = db.storage_get(context, storage_id)
    if storage_new['serial_number'] != storage_present['serial_number']:
        msg = (_("Serial number %s does not match "
                 "the existing storage serial number %s.") %
               (storage_new['serial_number'],
                storage_present['serial_number']))
        raise exception.StorageSerialNumberMismatch(msg)


def check_cm_consistency(context, cm_id, cm_new):
    """Check storage response returned by driver whether it matches the
    storage stored in database.

    :param context: The context of delfin.
    :type context: delfin.context.RequestContext
    :param cm_id: The uuid of storage in database.
    :type cm_id: string
    :param cm_new: The storage response returned by driver.
    :type cm_new: dict
    """
    if not cm_new:
        raise exception.CentralizedManagerNotFound()

    if not cm_new.get('serial_number'):
        msg = _("Serial number should be provided by cm.")
        raise exception.InvalidResults(msg)

    cm_present = db.centralized_manager_get(context, cm_id)
    if cm_new['serial_number'] != cm_present['serial_number']:
        msg = (_("Serial number %s does not match "
                 "the existing storage serial number %s.") %
               (cm_new['serial_number'],
                cm_present['serial_number']))
        raise exception.CentralizedManagerSerialNumberMismatch(msg)
