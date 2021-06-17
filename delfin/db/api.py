# Copyright 2020 The SODA Authors.
# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

"""Defines interface for DB access.

The underlying driver is loaded as a :class:`LazyPluggable`.

Functions in this module are imported into the delfin.db namespace. Call these
functions from delfin.db namespace, not the delfin.db.api namespace.

All functions in this module return objects that implement a dictionary-like
interface. Currently, many of these objects are sqlalchemy objects that
implement a dictionary interface. However, a future goal is to have all of
these objects be simple dictionaries.


**Related Flags**

:backend:  string to lookup in the list of LazyPluggable backends.
           `sqlalchemy` is the only supported backend right now.

:connection:  string specifying the sqlalchemy connection to use, like:
              `sqlite:///var/lib/delfin/delfin.sqlite`.

:enable_new_services:  when adding a new service to the database, is it in the
                       storage_pool of available hardware (Default: True)

"""
from oslo_config import cfg
from oslo_db import api as db_api

db_opts = [
    cfg.StrOpt('db_backend',
               default='sqlalchemy',
               help='The backend to use for database.'),
]

CONF = cfg.CONF
CONF.register_opts(db_opts, "database")

_BACKEND_MAPPING = {'sqlalchemy': 'delfin.db.sqlalchemy.api'}
IMPL = db_api.DBAPI(CONF.database.db_backend, backend_mapping=_BACKEND_MAPPING,
                    lazy=True)


def register_db():
    """Create database and tables."""
    IMPL.register_db()


def storage_get(context, storage_id):
    """Retrieve a storage device."""
    return IMPL.storage_get(context, storage_id)


def storage_get_all(context, marker=None, limit=None, sort_keys=None,
                    sort_dirs=None, filters=None, offset=None):
    """Retrieves all storage devices.

    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of storage
    """
    return IMPL.storage_get_all(context, marker, limit, sort_keys, sort_dirs,
                                filters, offset)


def storage_create(context, values):
    """Add a storage device from the values dictionary."""
    return IMPL.storage_create(context, values)


def storage_update(context, storage_id, values):
    """Update a storage device with the values dictionary."""
    return IMPL.storage_update(context, storage_id, values)


def storage_delete(context, storage_id):
    """Delete a storage device."""
    return IMPL.storage_delete(context, storage_id)


def centralized_manager_get(context, centralized_manager_id):
    """Retrieve a centralized_manager device."""
    return IMPL.centralized_manager_get(context, centralized_manager_id)


def centralized_manager_get_all(context, marker=None,
                                limit=None, sort_keys=None,
                                sort_dirs=None, filters=None, offset=None):
    """Retrieves all centralized_manager devices.

    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of centralized_manager
    """
    return IMPL.centralized_manager_get_all(context, marker, limit,
                                            sort_keys, sort_dirs,
                                            filters, offset)


def centralized_manager_create(context, values):
    """Add a centralized_manager device from the values dictionary."""
    return IMPL.centralized_manager_create(context, values)


def centralized_manager_update(context, centralized_manager_id, values):
    """Update a centralized_manager device with the values dictionary."""
    return IMPL.centralized_manager_update(context,
                                           centralized_manager_id, values)


def centralized_manager_delete(context, centralized_manager_id):
    """Delete a centralized_manager device."""
    return IMPL.centralized_manager_delete(context, centralized_manager_id)


def volume_create(context, values):
    """Create a volume from the values dictionary."""
    return IMPL.volume_create(context, values)


def volumes_create(context, values):
    """Create multiple volumes."""
    return IMPL.volumes_create(context, values)


def volume_update(context, volume_id, values):
    """Update a volume with the values dictionary."""
    return IMPL.volume_update(context, volume_id, values)


def volumes_update(context, values):
    """Update multiple volumes."""
    return IMPL.volumes_update(context, values)


def volumes_delete(context, values):
    """Delete multiple volumes."""
    return IMPL.volumes_delete(context, values)


def volume_get(context, volume_id):
    """Get a volume or raise an exception if it does not exist."""
    return IMPL.volume_get(context, volume_id)


def volume_get_all(context, marker=None, limit=None, sort_keys=None,
                   sort_dirs=None, filters=None, offset=None):
    """Retrieves all volumes.

    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of volumes
    """
    return IMPL.volume_get_all(context, marker, limit, sort_keys,
                               sort_dirs, filters, offset)


def volume_delete_by_storage(context, storage_id):
    """Delete all the volumes of a device."""
    return IMPL.volume_delete_by_storage(context, storage_id)


def storage_pool_create(context, storage_pool):
    """Add a storage_storage_pool."""
    return IMPL.storage_pool_create(context, storage_pool)


def storage_pools_create(context, storage_pools):
    """Add multiple storage_pools."""
    return IMPL.storage_pools_create(context, storage_pools)


def storage_pool_update(context, storage_pool_id, storage_pool):
    """Update a storage_pool."""
    return IMPL.storage_pool_update(context, storage_pool_id, storage_pool)


def storage_pools_update(context, storage_pools):
    """Update multiple storage_pools"""
    return IMPL.storage_pools_update(context, storage_pools)


def storage_pools_delete(context, storage_pools):
    """Delete storage_pools."""
    return IMPL.storage_pools_delete(context, storage_pools)


def storage_pool_get(context, storage_pool_id):
    """Get a storage_pool or raise an exception if it does not exist."""
    return IMPL.storage_pool_get(context, storage_pool_id)


def storage_pool_get_all(context, marker=None, limit=None, sort_keys=None,
                         sort_dirs=None, filters=None, offset=None):
    """Retrieves all  storage_pools.

    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of  storage_pools
    """
    return IMPL.storage_pool_get_all(context, marker, limit,
                                     sort_keys, sort_dirs, filters, offset)


def storage_pool_delete_by_storage(context, storage_id):
    """Delete all the storage_pool of a device."""
    return IMPL.storage_pool_delete_by_storage(context, storage_id)


def controllers_create(context, values):
    """Create multiple controllers."""
    return IMPL.controllers_create(context, values)


def controllers_update(context, values):
    """Update multiple controllers."""
    return IMPL.controllers_update(context, values)


def controllers_delete(context, values):
    """Delete multiple controllers."""
    return IMPL.controllers_delete(context, values)


def controller_create(context, values):
    """Create a controller from the values dictionary."""
    return IMPL.controller_create(context, values)


def controller_update(context, controller_id, values):
    """Update a controller with the values dictionary."""
    return IMPL.controller_update(context, controller_id, values)


def controller_get(context, controller_id):
    """Get a controller or raise an exception if it does not exist."""
    return IMPL.controller_get(context, controller_id)


def controller_delete_by_storage(context, storage_id):
    """Delete a controller or raise an exception if it does not exist."""
    return IMPL.controller_delete_by_storage(context, storage_id)


def controller_get_all(context, marker=None, limit=None, sort_keys=None,
                       sort_dirs=None, filters=None, offset=None):
    """Retrieves all controllers.
    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.
    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of controllers
    """
    return IMPL.controller_get_all(context, marker, limit, sort_keys,
                                   sort_dirs, filters, offset)


def ports_create(context, values):
    """Create multiple ports."""
    return IMPL.ports_create(context, values)


def ports_update(context, values):
    """Update multiple ports."""
    return IMPL.ports_update(context, values)


def ports_delete(context, values):
    """Delete multiple ports."""
    return IMPL.ports_delete(context, values)


def port_create(context, values):
    """Create a port from the values dictionary."""
    return IMPL.port_create(context, values)


def port_update(context, port_id, values):
    """Update a port with the values dictionary."""
    return IMPL.port_update(context, port_id, values)


def port_get(context, port_id):
    """Get a port or raise an exception if it does not exist."""
    return IMPL.port_get(context, port_id)


def port_delete_by_storage(context, storage_id):
    """Delete a port or raise an exception if it does not exist."""
    return IMPL.port_delete_by_storage(context, storage_id)


def port_get_all(context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
    """Retrieves all ports.
    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.
    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of controllers
    """
    return IMPL.port_get_all(context, marker, limit, sort_keys,
                             sort_dirs, filters, offset)


def disks_create(context, values):
    """Create multiple disks."""
    return IMPL.disks_create(context, values)


def disks_update(context, values):
    """Update multiple disks."""
    return IMPL.disks_update(context, values)


def disks_delete(context, values):
    """Delete multiple disks."""
    return IMPL.disks_delete(context, values)


def disk_create(context, values):
    """Create a disk from the values dictionary."""
    return IMPL.disk_create(context, values)


def disk_update(context, disk_id, values):
    """Update a disk withe the values dictionary."""
    return IMPL.disk_update(context, disk_id, values)


def disk_get(context, disk_id):
    """Get a disk or raise an exception if it does not exist."""
    return IMPL.disk_get(context, disk_id)


def disk_delete_by_storage(context, storage_id):
    """Delete a disk or raise an exception if it does not exist."""
    return IMPL.disk_delete_by_storage(context, storage_id)


def disk_get_all(context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
    """Retrieves all disks.

    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of disks
    """
    return IMPL.disk_get_all(context, marker, limit, sort_keys, sort_dirs,
                             filters, offset)


def filesystems_create(context, values):
    """Create multiple filesystems."""
    return IMPL.filesystems_create(context, values)


def filesystems_update(context, values):
    """Update multiple filesystems."""
    return IMPL.filesystems_update(context, values)


def filesystems_delete(context, values):
    """Delete multiple filesystems."""
    return IMPL.filesystems_delete(context, values)


def filesystem_create(context, values):
    """Create a filesystem from the values dictionary."""
    return IMPL.filesystem_create(context, values)


def filesystem_update(context, filesystem_id, values):
    """Update a filesystem with the values dictionary."""
    return IMPL.filesystem_update(context, filesystem_id, values)


def filesystem_get(context, filesystem_id):
    """Get a filesystem or raise an exception if it does not exist."""
    return IMPL.filesystem_get(context, filesystem_id)


def filesystem_delete_by_storage(context, storage_id):
    """Delete a filesystem or raise an exception if it does not exist."""
    return IMPL.filesystem_delete_by_storage(context, storage_id)


def filesystem_get_all(context, marker=None, limit=None, sort_keys=None,
                       sort_dirs=None, filters=None, offset=None):
    """Retrieves all filesystems.
    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.
    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of controllers
    """
    return IMPL.filesystem_get_all(context, marker, limit, sort_keys,
                                   sort_dirs, filters, offset)


def quotas_create(context, values):
    """Create multiple quotas."""
    return IMPL.quotas_create(context, values)


def quotas_update(context, values):
    """Update multiple quotas."""
    return IMPL.quotas_update(context, values)


def quotas_delete(context, values):
    """Delete multiple quotas."""
    return IMPL.quotas_delete(context, values)


def quota_create(context, values):
    """Create a quota from the values dictionary."""
    return IMPL.quota_create(context, values)


def quota_update(context, quota_id, values):
    """Update a quota with the values dictionary."""
    return IMPL.quota_update(context, quota_id, values)


def quota_get(context, quota_id):
    """Get a quota or raise an exception if it does not exist."""
    return IMPL.quota_get(context, quota_id)


def quota_delete_by_storage(context, storage_id):
    """Delete a quota or raise an exception if it does not exist."""
    return IMPL.quota_delete_by_storage(context, storage_id)


def quota_get_all(context, marker=None, limit=None, sort_keys=None,
                  sort_dirs=None, filters=None, offset=None):
    """Retrieves all quotas.
    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.
    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of controllers
    """
    return IMPL.quota_get_all(context, marker, limit, sort_keys,
                              sort_dirs, filters, offset)


def qtrees_create(context, values):
    """Create multiple qtrees."""
    return IMPL.qtrees_create(context, values)


def qtrees_update(context, values):
    """Update multiple qtrees."""
    return IMPL.qtrees_update(context, values)


def qtrees_delete(context, values):
    """Delete multiple qtrees."""
    return IMPL.qtrees_delete(context, values)


def qtree_create(context, values):
    """Create a qtree from the values dictionary."""
    return IMPL.qtree_create(context, values)


def qtree_update(context, qtree_id, values):
    """Update a qtree with the values dictionary."""
    return IMPL.qtree_update(context, qtree_id, values)


def qtree_get(context, qtree_id):
    """Get a qtree or raise an exception if it does not exist."""
    return IMPL.qtree_get(context, qtree_id)


def qtree_delete_by_storage(context, storage_id):
    """Delete a qtree or raise an exception if it does not exist."""
    return IMPL.qtree_delete_by_storage(context, storage_id)


def qtree_get_all(context, marker=None, limit=None, sort_keys=None,
                  sort_dirs=None, filters=None, offset=None):
    """Retrieves all qtrees.
    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.
    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of controllers
    """
    return IMPL.qtree_get_all(context, marker, limit, sort_keys,
                              sort_dirs, filters, offset)


def shares_create(context, values):
    """Create multiple shares."""
    return IMPL.shares_create(context, values)


def shares_update(context, values):
    """Update multiple shares."""
    return IMPL.shares_update(context, values)


def shares_delete(context, values):
    """Delete multiple shares."""
    return IMPL.shares_delete(context, values)


def share_create(context, values):
    """Create a share from the values dictionary."""
    return IMPL.share_create(context, values)


def share_update(context, share_id, values):
    """Update a share with the values dictionary."""
    return IMPL.share_update(context, share_id, values)


def share_get(context, share_id):
    """Get a share or raise an exception if it does not exist."""
    return IMPL.share_get(context, share_id)


def share_delete_by_storage(context, storage_id):
    """Delete a share or raise an exception if it does not exist."""
    return IMPL.share_delete_by_storage(context, storage_id)


def share_get_all(context, marker=None, limit=None, sort_keys=None,
                  sort_dirs=None, filters=None, offset=None):
    """Retrieves all shares.
    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.
    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of controllers
    """
    return IMPL.share_get_all(context, marker, limit, sort_keys,
                              sort_dirs, filters, offset)


def access_info_create(context, values):
    """Create a storage access information that used to connect
    to a specific storage device.
    """
    return IMPL.access_info_create(context, values)


def access_info_update(context, storage_id, values):
    """Update a storage access information with the values dictionary."""
    return IMPL.access_info_update(context, storage_id, values)


def access_info_get(context, storage_id):
    """Get a storage access information."""
    return IMPL.access_info_get(context, storage_id)


def access_info_delete(context, storage_id):
    """Delete a storage access information."""
    return IMPL.access_info_delete(context, storage_id)


def access_info_get_all(context, marker=None, limit=None, sort_keys=None,
                        sort_dirs=None, filters=None, offset=None):
    """Retrieves all storage access information.

    If no sort parameters are specified then the returned volumes are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of storage accesses
    """
    return IMPL.access_info_get_all(context, marker, limit,
                                    sort_keys, sort_dirs, filters, offset)


def is_orm_value(obj):
    """Check if object is an ORM field."""
    return IMPL.is_orm_value(obj)


def alert_source_create(context, values):
    """Create an alert source."""
    return IMPL.alert_source_create(context, values)


def alert_source_update(context, storage_id, values):
    """Update an alert source."""
    return IMPL.alert_source_update(context, storage_id, values)


def alert_source_get(context, storage_id):
    """Get an alert source."""
    return IMPL.alert_source_get(context, storage_id)


def alert_source_delete(context, storage_id):
    """Delete an alert source."""
    return IMPL.alert_source_delete(context, storage_id)


def alert_source_get_all(context, marker=None, limit=None, sort_keys=None,
                         sort_dirs=None, filters=None, offset=None):
    """Retrieves all alert sources.

    If no sort parameters are specified then the returned alert sources are
    sorted first by the 'created_at' key in descending order.

    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of storage accesses
    """
    return IMPL.alert_source_get_all(context, marker, limit, sort_keys,
                                     sort_dirs, filters, offset)


def task_create(context, values):
    """Create a task entry from the values dictionary."""
    return IMPL.task_create(context, values)


def task_update(context, task_id, values):
    """Update a task entry with the values dictionary."""
    return IMPL.task_update(context, task_id, values)


def task_get(context, task_id):
    """Get a task or raise an exception if it does not exist."""
    return IMPL.task_get(context, task_id)


def task_get_all(context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
    """Retrieves all  tasks.
    If no sort parameters are specified then the returned tasks are
    sorted first by the 'created_at' key and then by the 'id' key in
    descending order.
    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of  tasks
    """
    return IMPL.task_get_all(context, marker, limit,
                             sort_keys, sort_dirs, filters, offset)


def task_delete_by_storage(context, storage_id):
    """Delete all tasks of given storage or raise an exception if it
    does not exist.
    """
    return IMPL.task_delete_by_storage(context, storage_id)


def task_delete(context, task_id):
    """Delete a given task or raise an exception if it does not
    exist.
    """
    return IMPL.task_delete(context, task_id)


def failed_task_create(context, values):
    """Create a failed task entry from the values dictionary."""
    return IMPL.failed_task_create(context, values)


def failed_task_update(context, failed_task_id, values):
    """Update a failed task with the values dictionary."""
    return IMPL.failed_task_update(context, failed_task_id, values)


def failed_task_get(context, failed_task_id):
    """Get a failed task or raise an exception if it does not exist."""
    return IMPL.failed_task_get(context, failed_task_id)


def failed_task_get_all(context, marker=None, limit=None, sort_keys=None,
                        sort_dirs=None, filters=None, offset=None):
    """Retrieves all  failed tasks.
    If no sort parameters are specified then the returned failed tasks are
    sorted first by the 'created_at' key and then by the 'id' key in
    descending order.
    :param context: context of this request, it's helpful to trace the request
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys, for example
                      'desc' for descending order
    :param filters: dictionary of filters
    :param offset: number of items to skip
    :returns: list of failed tasks
    """
    return IMPL.failed_task_get_all(context, marker, limit,
                                    sort_keys, sort_dirs, filters, offset)


def failed_task_delete_by_task_id(context, task_id):
    """Delete all failed tasks of given task id or raise an exception
    if it does not exist.
    """
    return IMPL.failed_task_delete_by_task_id(context, task_id)


def failed_task_delete(context, failed_task_id):
    """Delete a given failed task or raise an exception if it does not
    exist.
    """
    return IMPL.failed_task_delete(context, failed_task_id)


def failed_task_delete_by_storage(context, storage_id):
    """Delete all failed tasks of given storage or raise an exception if it
    does not exist.
    """
    return IMPL.failed_task_delete_by_storage(context, storage_id)
