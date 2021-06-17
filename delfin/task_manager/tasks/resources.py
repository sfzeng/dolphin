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

import inspect

import decorator
from oslo_log import log

from delfin import coordination
from delfin import db
from delfin import exception
from delfin.common import constants
from delfin.drivers import api as driverapi
from delfin.i18n import _

LOG = log.getLogger(__name__)


def set_synced_after():
    @decorator.decorator
    def _set_synced_after(func, *args, **kwargs):
        call_args = inspect.getcallargs(func, *args, **kwargs)
        self = call_args['self']
        sync_result = constants.ResourceSync.SUCCEED
        ret = None
        try:
            ret = func(*args, **kwargs)
        except Exception:
            sync_result = constants.ResourceSync.FAILED
        lock = coordination.Lock(self.storage_id)
        with lock:
            try:
                storage = db.storage_get(self.context, self.storage_id)
            except exception.StorageNotFound:
                LOG.warn('Storage %s not found when set synced'
                         % self.storage_id)
            else:
                # One sync task done, sync status minus 1
                # When sync status get to 0
                # means all the sync tasks are completed
                if storage['sync_status'] != constants.SyncStatus.SYNCED:
                    storage['sync_status'] -= sync_result
                    db.storage_update(self.context, self.storage_id, storage)

        return ret

    return _set_synced_after


def check_deleted():
    @decorator.decorator
    def _check_deleted(func, *args, **kwargs):
        call_args = inspect.getcallargs(func, *args, **kwargs)
        self = call_args['self']
        ret = func(*args, **kwargs)
        # When context.read_deleted is 'yes', db.storage_get would
        # only get the storage whose 'deleted' tag is not default value
        self.context.read_deleted = 'yes'
        try:
            db.storage_get(self.context, self.storage_id)
        except exception.StorageNotFound:
            LOG.debug('Storage %s not found when checking deleted'
                      % self.storage_id)
        else:
            self.remove()
        self.context.read_deleted = 'no'
        return ret

    return _check_deleted


class StorageResourceTask(object):

    def __init__(self, context, storage_id):
        self.storage_id = storage_id
        self.context = context
        self.driver_api = driverapi.API()

    def _classify_resources(self, storage_resources, db_resources, key):
        """
        :param storage_resources:
        :param db_resources:
        :return: it will return three list add_list: the items present in
        storage but not in current_db. update_list:the items present in
        storage and in current_db. delete_id_list:the items present not in
        storage but present in current_db.
        """
        original_ids_in_db = [resource[key]
                              for resource in db_resources]
        delete_id_list = [resource['id'] for resource in db_resources]
        add_list = []
        update_list = []

        for resource in storage_resources:
            if resource[key] in original_ids_in_db:
                resource['id'] = db_resources[original_ids_in_db.index(
                    resource[key])]['id']
                delete_id_list.remove(resource['id'])
                update_list.append(resource)
            else:
                add_list.append(resource)

        return add_list, update_list, delete_id_list


class StorageDeviceTask(StorageResourceTask):
    def __init__(self, context, storage_id):
        super(StorageDeviceTask, self).__init__(context, storage_id)

    @check_deleted()
    @set_synced_after()
    def sync(self):
        """
        :return:
        """
        LOG.info('Syncing storage device for storage id:{0}'.format(
            self.storage_id))
        try:
            storage = self.driver_api.get_storage(self.context,
                                                  self.storage_id)

            db.storage_update(self.context, self.storage_id, storage)
        except Exception as e:
            msg = _('Failed to update storage entry in DB: {0}'
                    .format(e))
            LOG.error(msg)
            raise
        else:
            LOG.info("Syncing storage successful!!!")

    def remove(self):
        LOG.info('Remove storage device for storage id:{0}'
                 .format(self.storage_id))
        try:
            db.storage_delete(self.context, self.storage_id)
            db.access_info_delete(self.context, self.storage_id)
            db.alert_source_delete(self.context, self.storage_id)
        except Exception as e:
            LOG.error('Failed to update storage entry in DB: {0}'.format(e))


class StoragePoolTask(StorageResourceTask):
    def __init__(self, context, storage_id):
        super(StoragePoolTask, self).__init__(context, storage_id)

    @check_deleted()
    @set_synced_after()
    def sync(self):
        """
        :return:
        """
        LOG.info('Syncing storage pool for storage id:{0}'.format(
            self.storage_id))
        try:
            # collect the storage pools list from driver and database
            storage_pools = self.driver_api.list_storage_pools(self.context,
                                                               self.storage_id)
            db_pools = db.storage_pool_get_all(self.context,
                                               filters={"storage_id":
                                                        self.storage_id})

            add_list, update_list, delete_id_list = self._classify_resources(
                storage_pools, db_pools, 'native_storage_pool_id'
            )

            if delete_id_list:
                db.storage_pools_delete(self.context, delete_id_list)

            if update_list:
                db.storage_pools_update(self.context, update_list)

            if add_list:
                db.storage_pools_create(self.context, add_list)
        except Exception as e:
            msg = _('Failed to sync pools entry in DB: {0}'
                    .format(e))
            LOG.error(msg)
            raise
        else:
            LOG.info("Syncing storage pools successful!!!")

    def remove(self):
        LOG.info('Remove storage pools for storage id:{0}'.format(
            self.storage_id))
        db.storage_pool_delete_by_storage(self.context, self.storage_id)


class StorageVolumeTask(StorageResourceTask):
    def __init__(self, context, storage_id):
        super(StorageVolumeTask, self).__init__(context, storage_id)

    @check_deleted()
    @set_synced_after()
    def sync(self):
        """
        :return:
        """
        LOG.info('Syncing volumes for storage id:{0}'.format(self.storage_id))
        try:
            # collect the volumes list from driver and database
            storage_volumes = self.driver_api.list_volumes(self.context,
                                                           self.storage_id)
            db_volumes = db.volume_get_all(self.context,
                                           filters={"storage_id":
                                                    self.storage_id})

            add_list, update_list, delete_id_list = self._classify_resources(
                storage_volumes, db_volumes, 'native_volume_id'
            )
            LOG.info('###StorageVolumeTask for {0}:add={1},delete={2},'
                     'update={3}'.format(self.storage_id,
                                         len(add_list),
                                         len(delete_id_list),
                                         len(update_list)))
            if delete_id_list:
                db.volumes_delete(self.context, delete_id_list)

            if update_list:
                db.volumes_update(self.context, update_list)

            if add_list:
                db.volumes_create(self.context, add_list)
        except Exception as e:
            msg = _('Failed to sync volumes entry in DB: {0}'
                    .format(e))
            LOG.error(msg)
            raise
        else:
            LOG.info("Syncing volumes successful!!!")

    def remove(self):
        LOG.info('Remove volumes for storage id:{0}'.format(self.storage_id))
        db.volume_delete_by_storage(self.context, self.storage_id)


class StorageControllerTask(StorageResourceTask):
    def __init__(self, context, storage_id):
        super(StorageControllerTask, self).__init__(context, storage_id)

    @check_deleted()
    @set_synced_after()
    def sync(self):
        """
        :return:
        """
        LOG.info('Syncing controllers for storage id:{0}'
                 .format(self.storage_id))
        try:
            # collect the controllers list from driver and database
            storage_controllers = self.driver_api.list_controllers(
                self.context, self.storage_id)
            db_controllers = db.controller_get_all(self.context,
                                                   filters={"storage_id":
                                                            self.storage_id})

            add_list, update_list, delete_id_list = self._classify_resources(
                storage_controllers, db_controllers, 'native_controller_id'
            )

            LOG.info('###StorageControllerTask for {0}:add={1},delete={2},'
                     'update={3}'.format(self.storage_id,
                                         len(add_list),
                                         len(delete_id_list),
                                         len(update_list)))
            if delete_id_list:
                db.controllers_delete(self.context, delete_id_list)

            if update_list:
                db.controllers_update(self.context, update_list)

            if add_list:
                db.controllers_create(self.context, add_list)
        except AttributeError as e:
            LOG.error(e)
        except Exception as e:
            msg = _('Failed to sync controllers entry in DB: {0}'
                    .format(e))
            LOG.error(msg)
        else:
            LOG.info("Syncing controllers successful!!!")

    def remove(self):
        LOG.info('Remove controllers for storage id:{0}'
                 .format(self.storage_id))
        db.controller_delete_by_storage(self.context, self.storage_id)


class StoragePortTask(StorageResourceTask):
    def __init__(self, context, storage_id):
        super(StoragePortTask, self).__init__(context, storage_id)

    @check_deleted()
    @set_synced_after()
    def sync(self):
        """
        :return:
        """
        LOG.info('Syncing ports for storage id:{0}'.format(self.storage_id))
        try:
            # collect the ports list from driver and database
            storage_ports = self.driver_api.list_ports(self.context,
                                                       self.storage_id)
            db_ports = db.port_get_all(self.context,
                                       filters={"storage_id":
                                                self.storage_id})

            add_list, update_list, delete_id_list = self._classify_resources(
                storage_ports, db_ports, 'native_port_id'
            )

            LOG.info('###StoragePortTask for {0}:add={1},delete={2},'
                     'update={3}'.format(self.storage_id,
                                         len(add_list),
                                         len(delete_id_list),
                                         len(update_list)))
            if delete_id_list:
                db.ports_delete(self.context, delete_id_list)

            if update_list:
                db.ports_update(self.context, update_list)

            if add_list:
                db.ports_create(self.context, add_list)
        except AttributeError as e:
            LOG.error(e)
        except Exception as e:
            msg = _('Failed to sync ports entry in DB: {0}'
                    .format(e))
            LOG.error(msg)
        else:
            LOG.info("Syncing ports successful!!!")

    def remove(self):
        LOG.info('Remove ports for storage id:{0}'.format(self.storage_id))
        db.port_delete_by_storage(self.context, self.storage_id)


class StorageDiskTask(StorageResourceTask):
    def __init__(self, context, storage_id):
        super(StorageDiskTask, self).__init__(context, storage_id)

    @check_deleted()
    @set_synced_after()
    def sync(self):
        """
        :return:
        """
        LOG.info('Syncing disks for storage id:{0}'.format(self.storage_id))
        try:
            # collect the disks list from driver and database
            storage_disks = self.driver_api.list_disks(self.context,
                                                       self.storage_id)
            db_disks = db.disk_get_all(self.context,
                                       filters={"storage_id":
                                                self.storage_id})

            add_list, update_list, delete_id_list = self._classify_resources(
                storage_disks, db_disks, 'native_disk_id'
            )

            LOG.info('###StorageDiskTask for {0}:add={1},delete={2},'
                     'update={3}'.format(self.storage_id,
                                         len(add_list),
                                         len(delete_id_list),
                                         len(update_list)))
            if delete_id_list:
                db.disks_delete(self.context, delete_id_list)

            if update_list:
                db.disks_update(self.context, update_list)

            if add_list:
                db.disks_create(self.context, add_list)
        except AttributeError as e:
            LOG.error(e)
        except Exception as e:
            msg = _('Failed to sync disks entry in DB: {0}'
                    .format(e))
            LOG.error(msg)
        else:
            LOG.info("Syncing disks successful!!!")

    def remove(self):
        LOG.info('Remove disks for storage id:{0}'.format(self.storage_id))
        db.disk_delete_by_storage(self.context, self.storage_id)


class StorageQuotaTask(StorageResourceTask):
    def __init__(self, context, storage_id):
        super(StorageQuotaTask, self).__init__(context, storage_id)

    @check_deleted()
    @set_synced_after()
    def sync(self):
        """
        :return:
        """
        LOG.info('Syncing Quotas for storage id:{0}'.format(self.storage_id))
        try:
            # collect the quotas list from driver and database
            storage_quotas = self.driver_api.list_quotas(self.context,
                                                         self.storage_id)
            db_quotas = db.quota_get_all(self.context,
                                         filters={"storage_id":
                                                  self.storage_id})

            add_list, update_list, delete_id_list = self._classify_resources(
                storage_quotas, db_quotas, 'native_quota_id'
            )

            LOG.info('###StorageQuotaTask for {0}:add={1},delete={2},'
                     'update={3}'.format(self.storage_id,
                                         len(add_list),
                                         len(delete_id_list),
                                         len(update_list)))
            if delete_id_list:
                db.quotas_delete(self.context, delete_id_list)

            if update_list:
                db.quotas_update(self.context, update_list)

            if add_list:
                db.quotas_create(self.context, add_list)
        except AttributeError as e:
            LOG.error(e)
        except Exception as e:
            msg = _('Failed to sync Quotas entry in DB: {0}'
                    .format(e))
            LOG.error(msg)
        else:
            LOG.info("Syncing quotas successful!!!")

    def remove(self):
        LOG.info('Remove Quotas for storage id:{0}'.format(self.storage_id))
        db.quota_delete_by_storage(self.context, self.storage_id)


class StorageFilesystemTask(StorageResourceTask):
    def __init__(self, context, storage_id):
        super(StorageFilesystemTask, self).__init__(context, storage_id)

    @check_deleted()
    @set_synced_after()
    def sync(self):
        """
        :return:
        """
        LOG.info('Syncing Filesystems for storage id:{0}'
                 .format(self.storage_id))
        try:
            # collect the filesystems list from driver and database
            filesystems = self.driver_api.list_filesystems(
                self.context, self.storage_id)
            db_filesystems = db.filesystem_get_all(
                self.context, filters={"storage_id": self.storage_id})

            add_list, update_list, delete_id_list = self._classify_resources(
                filesystems, db_filesystems, 'native_filesystem_id'
            )

            LOG.info('###StorageFilesystemTask for {0}:add={1},delete={2},'
                     'update={3}'.format(self.storage_id,
                                         len(add_list),
                                         len(delete_id_list),
                                         len(update_list)))
            if delete_id_list:
                db.filesystems_delete(self.context, delete_id_list)

            if update_list:
                db.filesystems_update(self.context, update_list)

            if add_list:
                db.filesystems_create(self.context, add_list)

        except AttributeError as e:
            LOG.error(e)
        except NotImplementedError:
            # Ignore this exception because driver may not support it.
            pass
        except Exception as e:
            msg = _('Failed to sync filesystems entry in DB: {0}'
                    .format(e))
            LOG.error(msg)
        else:
            LOG.info("Syncing Filesystems successful!!!")

    def remove(self):
        LOG.info('Remove filesystems for storage id:{0}'
                 .format(self.storage_id))
        db.filesystem_delete_by_storage(self.context, self.storage_id)


class StorageQtreeTask(StorageResourceTask):
    def __init__(self, context, storage_id):
        super(StorageQtreeTask, self).__init__(context, storage_id)

    @check_deleted()
    @set_synced_after()
    def sync(self):
        """
        :return:
        """
        LOG.info('Syncing qtrees for storage id:{0}'
                 .format(self.storage_id))
        try:
            # collect the qtrees list from driver and database
            qtrees = self.driver_api.list_qtrees(
                self.context, self.storage_id)
            db_qtrees = db.qtree_get_all(
                self.context, filters={"storage_id": self.storage_id})

            add_list, update_list, delete_id_list = self._classify_resources(
                qtrees, db_qtrees, 'native_qtree_id'
            )

            LOG.info('###StorageQtreeTask for {0}:add={1},delete={2},'
                     'update={3}'.format(self.storage_id,
                                         len(add_list),
                                         len(delete_id_list),
                                         len(update_list)))
            if delete_id_list:
                db.qtrees_delete(self.context, delete_id_list)

            if update_list:
                db.qtrees_update(self.context, update_list)

            if add_list:
                db.qtrees_create(self.context, add_list)

        except AttributeError as e:
            LOG.error(e)
        except NotImplementedError:
            # Ignore this exception because driver may not support it.
            pass
        except Exception as e:
            msg = _('Failed to sync Qtrees entry in DB: {0}'
                    .format(e))
            LOG.error(msg)
        else:
            LOG.info("Syncing Qtrees successful!!!")

    def remove(self):
        LOG.info('Remove qtrees for storage id:{0}'
                 .format(self.storage_id))
        db.qtree_delete_by_storage(self.context, self.storage_id)


class StorageShareTask(StorageResourceTask):
    def __init__(self, context, storage_id):
        super(StorageShareTask, self).__init__(context, storage_id)

    @check_deleted()
    @set_synced_after()
    def sync(self):
        """
        :return:
        """
        LOG.info('Syncing shares for storage id:{0}'
                 .format(self.storage_id))
        try:
            # collect the shares list from driver and database
            storage_shares = self.driver_api.list_shares(
                self.context, self.storage_id)
            db_shares = db.share_get_all(
                self.context, filters={"storage_id": self.storage_id})

            add_list, update_list, delete_id_list = self._classify_resources(
                storage_shares, db_shares, 'native_share_id'
            )

            LOG.info('###StorageShareTask for {0}:add={1},delete={2},'
                     'update={3}'.format(self.storage_id,
                                         len(add_list),
                                         len(delete_id_list),
                                         len(update_list)))
            if delete_id_list:
                db.shares_delete(self.context, delete_id_list)

            if update_list:
                db.shares_update(self.context, update_list)

            if add_list:
                db.shares_create(self.context, add_list)
        except AttributeError as e:
            LOG.error(e)
        except NotImplementedError:
            # Ignore this exception because driver may not support it.
            pass
        except Exception as e:
            msg = _('Failed to sync Shares entry in DB: {0}'
                    .format(e))
            LOG.error(msg)
        else:
            LOG.info("Syncing Shares successful!!!")

    def remove(self):
        LOG.info('Remove shares for storage id:{0}'
                 .format(self.storage_id))
        db.share_delete_by_storage(self.context, self.storage_id)


class CentralizedManagerTask(object):
    def __init__(self, context, cm_id):
        self.cm_id = cm_id
        self.context = context
        self.driver_api = driverapi.API()

    @check_deleted()
    @set_synced_after()
    def sync(self):
        """
        :return:
        """
        LOG.info('Syncing centralized manager for cm id:{0}'.format(
            self.cm_id))
        try:
            cm = self.driver_api.\
                get_centralized_manager(self.context, self.cm_id)

            db.centralized_manager_update(self.context, self.cm_id, cm)
        except Exception as e:
            msg = _('Failed to update cm entry in DB: {0}'
                    .format(e))
            LOG.error(msg)
            raise
        else:
            LOG.info("Syncing centralized managers successful!!!")

    def remove(self):
        LOG.info('Remove centralized manager for cm id:{0}'
                 .format(self.cm_id))
        try:
            db.centralized_manager_delete(self.context, self.cm_id)
            db.access_info_delete(self.context, self.cm_id)
        except Exception as e:
            LOG.error('Failed to update centralized manager entry in DB: {0}'
                      .format(e))
