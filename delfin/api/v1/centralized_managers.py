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

import six
import copy

from oslo_log import log
from oslo_utils import uuidutils

from delfin import db
from delfin.api import api_utils
from delfin.api import validation
from delfin.api.common import wsgi
from delfin.api.schemas import storages as schema_storages
from delfin.api.v1.storages import \
    create_performance_monitoring_task, set_synced_if_ok
from delfin.api.views import centralized_managers as cm_view
from delfin.common import constants
from delfin.drivers import helper
from delfin.drivers import api as driverapi
from delfin.i18n import _
from delfin import coordination
from delfin import exception
from delfin.task_manager.tasks import resources
from delfin.task_manager import rpcapi as task_rpcapi
from delfin.task_manager.tasks import telemetry as task_telemetry

LOG = log.getLogger(__name__)


class CentralizedManagerController(wsgi.Controller):
    def __init__(self):
        super(CentralizedManagerController, self).__init__()
        self.task_rpcapi = task_rpcapi.TaskAPI()
        self.driver_api = driverapi.API()
        self.search_options = ['id', 'vendor',
                               'model', 'serial_number']

    def _get_cms_search_options(self):
        """Return storage_pools search options allowed ."""
        return self.search_options

    def _dm_exist(self, context, access_info):
        access_info_dict = copy.deepcopy(access_info)

        # Remove unrelated query fields
        unrelated_fields = ['username', 'password']
        for access in constants.ACCESS_TYPE:
            if access_info_dict.get(access):
                for key in unrelated_fields:
                    access_info_dict[access].pop(key)

        # Check if storage is registered
        access_info_list = db.access_info_get_all(context,
                                                  filters=access_info_dict)
        for _access_info in access_info_list:
            try:
                cm = db.centralized_manager_get(
                    context, _access_info['storage_id'])
                if cm:
                    LOG.error("CM %s has same access "
                              "information." % cm['id'])
                    return True
            except exception.CentralizedManagerNotFound:
                # Suppose storage was not saved successfully after access
                # information was saved in database when registering storage.
                # Therefore, removing access info if storage doesn't exist to
                # ensure the database has no residual data.
                LOG.debug("Remove residual access information.")
                db.access_info_delete(context, _access_info['storage_id'])

        return False

    def show(self, req, id):
        ctxt = req.environ['delfin.context']
        cm = db.centralized_manager_get(ctxt, id)
        return cm_view.build_centralized_manager(cm)

    def index(self, req):
        ctxt = req.environ['delfin.context']
        query_params = {}
        query_params.update(req.GET)
        # update options  other than filters
        sort_keys, sort_dirs = api_utils.get_sort_params(query_params)
        marker, limit, offset = api_utils.get_pagination_params(query_params)
        # strip out options except supported search  options
        api_utils.remove_invalid_options(ctxt, query_params,
                                         self._get_cms_search_options())

        cms = db.centralized_manager_get_all(ctxt, marker, limit, sort_keys,
                                             sort_dirs, query_params, offset)
        return cm_view.build_centralized_managers(cms)

    @wsgi.response(201)
    @validation.schema(schema_storages.create)
    def create(self, req, body):
        """Register a new storage device."""
        ctxt = req.environ['delfin.context']
        access_info_dict = body

        # Lock to avoid synchronous creating.
        for access in constants.ACCESS_TYPE:
            if access_info_dict.get(access) is not None:
                host = access_info_dict.get(access).get('host')
                break
        lock_name = 'cm-create-' + host
        lock = coordination.Lock(lock_name)

        with lock:
            if self._dm_exist(ctxt, access_info_dict):
                raise exception.CentralizedManagerAlreadyExists()
            cm = self.driver_api.discover_centralized_manager(
                ctxt, access_info_dict)

        # Registration success, sync resource collection for this storage
        for storage in cm['storages']:
            self._create_storage(ctxt, storage['id'])
        return cm_view.build_centralized_manager(cm)

    @wsgi.response(202)
    def delete(self, req, id):
        ctxt = req.environ['delfin.context']
        cm = db.centralized_manager_get(ctxt, id)
        db.centralized_manager_delete(ctxt, id)
        for storage in cm['storages']:
            self._delete_storage(ctxt, storage['id'])

    @wsgi.response(202)
    def sync_all(self, req):
        """
        :param req:
        :return: it's a Asynchronous call. so return 202 on success. sync_all
        api performs the storage device info, storage_pool,
         volume etc. tasks on each registered storage device.
        """
        ctxt = req.environ['delfin.context']

        db_cms = db.centralized_manager_get_all(ctxt)
        LOG.debug("Total {0} registered CMs found in database".
                  format(len(db_cms)))

        for db_cm in db_cms:
            self._sync_cm(ctxt, db_cm['storages'], db_cm['id'])

    @wsgi.response(202)
    def sync(self, req, id):
        """
        :param req:
        :param id:
        :return:
        """
        ctxt = req.environ['delfin.context']
        db_cm = db.centralized_manager_get(ctxt, id)
        if db_cm:
            self._sync_cm(ctxt, db_cm['storages'], id)

    def _sync_cm(self, ctxt, storages, id):
        delete_list = []
        db_storages = []
        for storage in storages:
            db_storages.append(storage['serial_number'])
            delete_list.append(storage['serial_number'])

        cm = self.driver_api.get_centralized_manager(ctxt, id)
        if not cm:
            raise exception.CentralizedManagerNotFound

        for storage in cm['storages']:
            if storage['serial_number'] in db_storages:
                delete_list.remove(storage['serial_number'])
            else:
                # Create storages
                access_info = db.access_info_get(ctxt, id)
                helper.check_storage_repetition(ctxt, storage)
                storage['id'] = six.text_type(
                    uuidutils.generate_uuid())
                access_info['storage_id'] = storage['id']
                db.access_info_create(ctxt, access_info)
                db.storage_create(ctxt, storage)

                self._create_storage(ctxt, storage['id'])

        # Update cm
        db.centralized_manager_update(ctxt, id, cm)

        # Delete stale storages
        delete_id_list = []
        for storage in storages:
            if storage['serial_number'] in delete_list:
                delete_id_list.append(storage['id'])

        for storage_id in delete_list:
            self._delete_storage(ctxt, storage_id)

    def _sync_storage(self, ctxt, id):
        """
        :param ctxt:
        :param id:
        :return:
        """
        storage = db.storage_get(ctxt, id)
        resource_count = len(resources.StorageResourceTask.__subclasses__())
        set_synced_if_ok(ctxt, storage['id'], resource_count)
        for subclass in resources.StorageResourceTask.__subclasses__():
            self.task_rpcapi.sync_storage_resource(
                ctxt,
                storage['id'],
                subclass.__module__ + '.' + subclass.__name__)

    def _create_storage(self, ctxt, storage_id):
        try:
            resource_count = len(
                resources.StorageResourceTask.__subclasses__())
            set_synced_if_ok(ctxt, storage_id, resource_count)
            for subclass in resources.StorageResourceTask.__subclasses__():
                self.task_rpcapi.sync_storage_resource(
                    ctxt,
                    storage_id,
                    subclass.__module__ + '.' + subclass.__name__)

            # Post registration, trigger alert sync
            self.task_rpcapi.sync_storage_alerts(ctxt, storage_id,
                                                 query_para=None)
        except Exception as e:
            # Unexpected error occurred, while syncing resources.
            msg = _('Failed to sync resources for storage: %(storage)s. '
                    'Error: %(err)s') % {'storage': storage_id, 'err': e}
            LOG.error(msg)

        try:
            # Trigger Performance monitoring
            capabilities = self.driver_api.get_capabilities(
                context=ctxt, storage_id=storage_id)
            validation.validate_capabilities(capabilities)
            create_performance_monitoring_task(ctxt, storage_id,
                                               capabilities)
        except exception.EmptyResourceMetrics:
            msg = _("Resource metric provided by "
                    "capabilities is empty for "
                    "storage: %s") % storage_id
            LOG.info(msg)
        except Exception as e:
            # Unexpected error occurred, while performance monitoring.
            msg = _('Failed to trigger performance '
                    'monitoring for storage: '
                    '%(storage)s. Error: '
                    '%(err)s') % {'storage': storage_id,
                                  'err': six.text_type(e)}
            LOG.error(msg)

    def _delete_storage(self, ctxt, storage_id):
        for subclass in resources.StorageResourceTask.__subclasses__():
            self.task_rpcapi.remove_storage_resource(
                ctxt,
                storage_id,
                subclass.__module__ + '.' + subclass.__name__)

        for subclass in task_telemetry.TelemetryTask.__subclasses__():
            self.task_rpcapi.remove_telemetry_instances(ctxt,
                                                        storage_id,
                                                        subclass.__module__ +
                                                        '.'
                                                        + subclass.__name__)
        self.task_rpcapi.remove_storage_in_cache(ctxt, storage_id)


def create_resource():
    return wsgi.Resource(CentralizedManagerController())
