# Copyright 2020 The SODA Authors.
# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright (c) 2014 Mirantis, Inc.
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

"""Implementation of SQLAlchemy backend."""

import sys

import six
import sqlalchemy
from oslo_config import cfg
from oslo_db import options as db_options
from oslo_db.sqlalchemy import session
from oslo_db.sqlalchemy import utils as db_utils
from oslo_log import log
from oslo_utils import uuidutils, timeutils
from sqlalchemy import create_engine

from delfin import exception
from delfin.common import sqlalchemyutils
from delfin.db.sqlalchemy import models
from delfin.db.sqlalchemy.models import Storage, AccessInfo
from delfin.i18n import _

CONF = cfg.CONF
LOG = log.getLogger(__name__)
_FACADE = None

_DEFAULT_SQL_CONNECTION = 'sqlite:///'
db_options.set_defaults(cfg.CONF,
                        connection=_DEFAULT_SQL_CONNECTION)


def apply_sorting(model, query, sort_key, sort_dir):
    if sort_dir.lower() not in ('desc', 'asc'):
        msg = (("Wrong sorting data provided: sort key is '%(sort_key)s' "
                "and sort order is '%(sort_dir)s'.") %
               {"sort_key": sort_key, "sort_dir": sort_dir})
        raise exception.InvalidInput(msg)

    sort_attr = getattr(model, sort_key)
    sort_method = getattr(sort_attr, sort_dir.lower())
    return query.order_by(sort_method())


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = session.EngineFacade.from_config(cfg.CONF)
    return _FACADE


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def register_db():
    """Create database and tables."""
    models = (Storage,
              AccessInfo
              )
    engine = create_engine(CONF.database.connection, echo=False)
    for model in models:
        model.metadata.create_all(engine)


def _process_model_like_filter(model, query, filters):
    """Applies regex expression filtering to a query.

    :param model: model to apply filters to
    :param query: query to apply filters to
    :param filters: dictionary of filters with regex values
    :returns: the updated query.
    """
    if query is None:
        return query

    for key in sorted(filters):
        column_attr = getattr(model, key)
        if 'property' == type(column_attr).__name__:
            continue
        value = filters[key]
        if not (isinstance(value, (six.string_types, int))):
            continue
        query = query.filter(
            column_attr.op('LIKE')(u'%%%s%%' % value))
    return query


def apply_like_filters(model):
    def decorator_filters(process_exact_filters):
        def _decorator(query, filters):
            exact_filters = filters.copy()
            regex_filters = {}
            for key, value in filters.items():
                # NOTE(tommylikehu): For inexact match, the filter keys
                # are in the format of 'key~=value'
                if key.endswith('~'):
                    exact_filters.pop(key)
                    regex_filters[key.rstrip('~')] = value
            query = process_exact_filters(query, exact_filters)
            return _process_model_like_filter(model, query, regex_filters)

        return _decorator

    return decorator_filters


def is_valid_model_filters(model, filters, exclude_list=None):
    """Return True if filter values exist on the model

    :param model: a Delfin model
    :param filters: dictionary of filters
    """
    for key in filters.keys():
        if exclude_list and key in exclude_list:
            continue
        if key == 'metadata':
            if not isinstance(filters[key], dict):
                LOG.debug("Metadata filter value is not valid dictionary")
                return False
            continue
        try:
            key = key.rstrip('~')
            getattr(model, key)
        except AttributeError:
            LOG.debug("'%s' filter key is not valid.", key)
            return False
    return True


def access_info_create(context, values):
    """Create a storage access information."""
    if not values.get('storage_id'):
        values['storage_id'] = uuidutils.generate_uuid()

    access_info_ref = models.AccessInfo()
    access_info_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(access_info_ref)

    return _access_info_get(context,
                            access_info_ref['storage_id'],
                            session=session)


def access_info_update(context, storage_id, values):
    """Update a storage access information with the values dictionary."""
    session = get_session()
    with session.begin():
        _access_info_get(context, storage_id, session).update(values)
        return _access_info_get(context, storage_id, session)


def access_info_delete(context, storage_id):
    """Delete a storage access information."""
    _access_info_get_query(context). \
        filter_by(storage_id=storage_id).delete()


def access_info_get(context, storage_id):
    """Get a storage access information."""
    return _access_info_get(context, storage_id)


def _access_info_get(context, storage_id, session=None):
    result = (_access_info_get_query(context, session=session)
              .filter_by(storage_id=storage_id)
              .first())

    if not result:
        raise exception.AccessInfoNotFound(storage_id)

    return result


def _access_info_get_query(context, session=None):
    return model_query(context, models.AccessInfo, session=session)


def access_info_get_all(context, marker=None, limit=None, sort_keys=None,
                        sort_dirs=None, filters=None, offset=None):
    """Retrieves all storage access information."""
    session = get_session()
    with session.begin():
        query = _generate_paginate_query(context, session, models.AccessInfo,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.AccessInfo)
def _process_access_info_filters(query, filters):
    """Common filter processing for AccessInfo queries."""
    if filters:
        if not is_valid_model_filters(models.AccessInfo, filters):
            return
        query = query.filter_by(**filters)

    return query


def storage_create(context, values):
    """Add a storage device from the values dictionary."""
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    storage_ref = models.Storage()
    storage_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(storage_ref)

    return _storage_get(context,
                        storage_ref['id'],
                        session=session)


def storage_update(context, storage_id, values):
    """Update a storage device with the values dictionary."""
    session = get_session()
    with session.begin():
        query = _storage_get_query(context, session)
        result = query.filter_by(id=storage_id).update(values)
    return result


def storage_get(context, storage_id):
    """Retrieve a storage device."""
    return _storage_get(context, storage_id)


def _storage_get(context, storage_id, session=None):
    result = (_storage_get_query(context, session=session)
              .filter_by(id=storage_id)
              .first())

    if not result:
        raise exception.StorageNotFound(storage_id)

    return result


def _storage_get_query(context, session=None):
    read_deleted = context.read_deleted
    kwargs = dict()

    if read_deleted in ('no', 'n', False):
        kwargs['deleted'] = False
    elif read_deleted in ('yes', 'y', True):
        kwargs['deleted'] = True

    return model_query(context, models.Storage, session=session, **kwargs)


def storage_get_all(context, marker=None, limit=None, sort_keys=None,
                    sort_dirs=None, filters=None, offset=None):
    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.Storage,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No storages   match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.Storage)
def _process_storage_info_filters(query, filters):
    """Common filter processing for Storages queries."""
    if filters:
        if not is_valid_model_filters(models.Storage, filters):
            return
        query = query.filter_by(**filters)
    return query


def storage_delete(context, storage_id):
    """Delete a storage device."""
    delete_info = {'deleted': True, 'deleted_at': timeutils.utcnow()}
    _storage_get_query(context).filter_by(id=storage_id).update(delete_info)


def centralized_manager_create(context, values):
    """Add a centralized_manager device from the values dictionary."""
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    centralized_manager_ref = models.CentralizedManager()
    centralized_manager_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(centralized_manager_ref)

    return _centralized_manager_get(context,
                                    centralized_manager_ref['id'],
                                    session=session)


def centralized_manager_update(context, centralized_manager_id, values):
    """Update a centralized_manager device with the values dictionary."""
    session = get_session()
    with session.begin():
        query = _centralized_manager_get_query(context, session)
        result = query.filter_by(
            id=centralized_manager_id).update(values)
    return result


def centralized_manager_get(context, centralized_manager_id):
    """Retrieve a centralized_manager device."""
    return _centralized_manager_get(context, centralized_manager_id)


def _centralized_manager_get(context, centralized_manager_id, session=None):
    result = (_centralized_manager_get_query(context, session=session)
              .filter_by(id=centralized_manager_id)
              .first())

    if not result:
        raise exception.CentralizedManagerNotFound(centralized_manager_id)

    return result


def _centralized_manager_get_query(context, session=None):
    read_deleted = context.read_deleted
    kwargs = dict()

    if read_deleted in ('no', 'n', False):
        kwargs['deleted'] = False
    elif read_deleted in ('yes', 'y', True):
        kwargs['deleted'] = True

    return model_query(context, models.CentralizedManager,
                       session=session, **kwargs)


def centralized_manager_get_all(context, marker=None,
                                limit=None, sort_keys=None,
                                sort_dirs=None, filters=None, offset=None):
    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session,
                                         models.CentralizedManager,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No centralized_managers   match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.CentralizedManager)
def _process_centralized_manager_info_filters(query, filters):
    """Common filter processing for CentralizedManagers queries."""
    if filters:
        if not is_valid_model_filters(models.CentralizedManager, filters):
            return
        query = query.filter_by(**filters)
    return query


def centralized_manager_delete(context, centralized_manager_id):
    """Delete a centralized_manager device."""
    delete_info = {'deleted': True, 'deleted_at': timeutils.utcnow()}
    _centralized_manager_get_query(context).filter_by(
        id=centralized_manager_id).update(delete_info)


def _volume_get_query(context, session=None):
    return model_query(context, models.Volume, session=session)


def _volume_get(context, volume_id, session=None):
    result = (_volume_get_query(context, session=session)
              .filter_by(id=volume_id)
              .first())

    if not result:
        raise exception.VolumeNotFound(volume_id)

    return result


def volume_create(context, values):
    """Create a volume."""
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    vol_ref = models.Volume()
    vol_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(vol_ref)

    return _volume_get(context,
                       vol_ref['id'],
                       session=session)


def volumes_create(context, volumes):
    """Create multiple volumes."""
    session = get_session()
    vol_refs = []
    with session.begin():

        for vol in volumes:
            LOG.debug('adding new volume for native_volume_id {0}:'
                      .format(vol.get('native_volume_id')))
            if not vol.get('id'):
                vol['id'] = uuidutils.generate_uuid()

            vol_ref = models.Volume()
            vol_ref.update(vol)
            vol_refs.append(vol_ref)

        session.add_all(vol_refs)

    return vol_refs


def volumes_delete(context, volumes_id_list):
    """Delete multiple volumes."""
    session = get_session()
    with session.begin():
        for vol_id in volumes_id_list:
            LOG.debug('deleting volume {0}:'.format(vol_id))
            query = _volume_get_query(context, session)
            result = query.filter_by(id=vol_id).delete()

            if not result:
                LOG.error(exception.VolumeNotFound(vol_id))
    return


def volume_update(context, vol_id, values):
    """Update a volume."""
    session = get_session()
    with session.begin():
        _volume_get(context, vol_id, session).update(values)
    return _volume_get(context, vol_id, session)


def volumes_update(context, volumes):
    """Update multiple volumes."""
    session = get_session()
    with session.begin():
        for vol in volumes:
            LOG.debug('updating volume {0}:'.format(vol.get('id')))
            query = _volume_get_query(context, session)
            result = query.filter_by(id=vol.get('id')
                                     ).update(vol)

            if not result:
                LOG.error(exception.VolumeNotFound(vol.get('id')))


def volume_get(context, volume_id):
    """Get a volume or raise an exception if it does not exist."""
    return _volume_get(context, volume_id)


def volume_get_all(context, marker=None, limit=None, sort_keys=None,
                   sort_dirs=None, filters=None, offset=None):
    """Retrieves all storage volumes."""
    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.Volume,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset)
        # No volume would match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.Volume)
def _process_volume_info_filters(query, filters):
    """Common filter processing for volumes queries."""
    if filters:
        if not is_valid_model_filters(models.Volume, filters):
            return
        query = query.filter_by(**filters)

    return query


def volume_delete_by_storage(context, storage_id):
    """Delete all the volumes of a device"""
    _volume_get_query(context).filter_by(storage_id=storage_id).delete()


def _storage_pool_get_query(context, session=None):
    return model_query(context, models.StoragePool, session=session)


def _storage_pool_get(context, storage_pool_id, session=None):
    result = (_storage_pool_get_query(context, session=session)
              .filter_by(id=storage_pool_id)
              .first())

    if not result:
        raise exception.StoragePoolNotFound(storage_pool_id)

    return result


def storage_pool_create(context, values):
    """Create a storage_pool from the values dictionary."""
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    storage_pool_ref = models.StoragePool()
    storage_pool_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(storage_pool_ref)

    return _storage_pool_get(context,
                             storage_pool_ref['id'],
                             session=session)


def storage_pools_create(context, storage_pools):
    """Create a storage_pool from the values dictionary."""
    session = get_session()
    storage_pool_refs = []
    with session.begin():

        for storage_pool in storage_pools:
            LOG.debug('adding new storage_pool for native_storage_pool_id {0}:'
                      .format(storage_pool.get('native_storage_pool_id')))
            if not storage_pool.get('id'):
                storage_pool['id'] = uuidutils.generate_uuid()

            storage_pool_ref = models.StoragePool()
            storage_pool_ref.update(storage_pool)
            storage_pool_refs.append(storage_pool_ref)

        session.add_all(storage_pool_refs)

    return storage_pool_refs


def storage_pools_delete(context, storage_pools_id_list):
    """Delete multiple storage_pools with the storage_pools dictionary."""
    session = get_session()
    with session.begin():
        for storage_pool_id in storage_pools_id_list:
            LOG.debug('deleting storage_pool {0}:'.format(storage_pool_id))
            query = _storage_pool_get_query(context, session)
            result = query.filter_by(id=storage_pool_id).delete()

            if not result:
                LOG.error(exception.StoragePoolNotFound(storage_pool_id))

    return


def storage_pool_update(context, storage_pool_id, values):
    """Update a storage_pool withe the values dictionary."""
    session = get_session()

    with session.begin():
        query = _storage_pool_get_query(context, session)
        result = query.filter_by(id=storage_pool_id).update(values)

        if not result:
            raise exception.StoragePoolNotFound(storage_pool_id)

    return result


def storage_pools_update(context, storage_pools):
    """Update multiple storage_pools withe the storage_pools dictionary."""
    session = get_session()

    with session.begin():
        storage_pool_refs = []

        for storage_pool in storage_pools:
            LOG.debug('updating storage_pool {0}:'.format(
                storage_pool.get('id')))
            query = _storage_pool_get_query(context, session)
            result = query.filter_by(id=storage_pool.get('id')
                                     ).update(storage_pool)

            if not result:
                LOG.error(exception.StoragePoolNotFound(storage_pool.get(
                    'id')))
            else:
                storage_pool_refs.append(result)

    return storage_pool_refs


def storage_pool_get(context, storage_pool_id):
    """Get a storage_pool or raise an exception if it does not exist."""
    return _storage_pool_get(context, storage_pool_id)


def storage_pool_get_all(context, marker=None, limit=None, sort_keys=None,
                         sort_dirs=None, filters=None, offset=None):
    """Retrieves all storage storage_pools."""
    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.StoragePool,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No storage_pool would match, return empty list
        if query is None:
            return []
        return query.all()


def storage_pool_delete_by_storage(context, storage_id):
    """Delete all the storage_pools of a storage device"""
    _storage_pool_get_query(context).filter_by(storage_id=storage_id).delete()


@apply_like_filters(model=models.StoragePool)
def _process_storage_pool_info_filters(query, filters):
    """Common filter processing for storage_pools queries."""
    if filters:
        if not is_valid_model_filters(models.StoragePool, filters):
            return
        query = query.filter_by(**filters)

    return query


def controllers_create(context, controllers):
    """Create multiple controllers."""
    session = get_session()
    controllers_refs = []
    with session.begin():

        for controller in controllers:
            LOG.debug('adding new controller for native_controller_id {0}:'
                      .format(controller.get('native_controller_id')))
            if not controller.get('id'):
                controller['id'] = uuidutils.generate_uuid()

            controller_ref = models.Controller()
            controller_ref.update(controller)
            controllers_refs.append(controller_ref)

        session.add_all(controllers_refs)

    return controllers_refs


def controllers_update(context, controllers):
    """Update multiple controllers."""
    session = get_session()

    with session.begin():
        controller_refs = []

        for controller in controllers:
            LOG.debug('updating controller {0}:'.format(
                controller.get('id')))
            query = _controller_get_query(context, session)
            result = query.filter_by(id=controller.get('id')
                                     ).update(controller)

            if not result:
                LOG.error(exception.ControllerNotFound(controller.get(
                    'id')))
            else:
                controller_refs.append(result)

    return controller_refs


def controllers_delete(context, controllers_id_list):
    """Delete multiple controllers."""
    session = get_session()
    with session.begin():
        for controller_id in controllers_id_list:
            LOG.debug('deleting controller {0}:'.format(controller_id))
            query = _controller_get_query(context, session)
            result = query.filter_by(id=controller_id).delete()

            if not result:
                LOG.error(exception.ControllerNotFound(controller_id))

    return


def _controller_get_query(context, session=None):
    return model_query(context, models.Controller, session=session)


def _controller_get(context, controller_id, session=None):
    result = (_controller_get_query(context, session=session)
              .filter_by(id=controller_id)
              .first())

    if not result:
        raise exception.ControllerNotFound(controller_id)

    return result


def controller_create(context, values):
    """Create a controller from the values dictionary."""
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    controller_ref = models.Controller()
    controller_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(controller_ref)

    return _controller_get(context,
                           controller_ref['id'],
                           session=session)


def controller_update(context, controller_id, values):
    """Update a controller with the values dictionary."""
    session = get_session()

    with session.begin():
        query = _controller_get_query(context, session)
        result = query.filter_by(id=controller_id).update(values)

        if not result:
            raise exception.ControllerNotFound(controller_id)

    return result


def controller_get(context, controller_id):
    """Get a controller or raise an exception if it does not exist."""
    return _controller_get(context, controller_id)


def controller_delete_by_storage(context, storage_id):
    """Delete a controller or raise an exception if it does not exist."""
    _controller_get_query(context).filter_by(storage_id=storage_id).delete()


def controller_get_all(context, marker=None, limit=None, sort_keys=None,
                       sort_dirs=None, filters=None, offset=None):
    """Retrieves all controllers."""
    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.Controller,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No Controller would match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.Controller)
def _process_controller_info_filters(query, filters):
    """Common filter processing for controllers queries."""
    if filters:
        if not is_valid_model_filters(models.Controller, filters):
            return
        query = query.filter_by(**filters)

    return query


def ports_create(context, ports):
    """Create multiple ports."""
    session = get_session()
    ports_refs = []
    with session.begin():

        for port in ports:
            LOG.debug('adding new port for native_port_id {0}:'
                      .format(port.get('native_port_id')))
            if not port.get('id'):
                port['id'] = uuidutils.generate_uuid()

            port_ref = models.Port()
            port_ref.update(port)
            ports_refs.append(port_ref)

        session.add_all(ports_refs)

    return ports_refs


def ports_update(context, ports):
    """Update multiple ports."""
    session = get_session()

    with session.begin():
        port_refs = []

        for port in ports:
            LOG.debug('updating port {0}:'.format(
                port.get('id')))
            query = _port_get_query(context, session)
            result = query.filter_by(id=port.get('id')
                                     ).update(port)

            if not result:
                LOG.error(exception.PortNotFound(port.get(
                    'id')))
            else:
                port_refs.append(result)

    return port_refs


def ports_delete(context, ports_id_list):
    """Delete multiple ports."""
    session = get_session()
    with session.begin():
        for port_id in ports_id_list:
            LOG.debug('deleting port {0}:'.format(port_id))
            query = _port_get_query(context, session)
            result = query.filter_by(id=port_id).delete()

            if not result:
                LOG.error(exception.PortNotFound(port_id))
    return


def _port_get_query(context, session=None):
    return model_query(context, models.Port, session=session)


def _port_get(context, port_id, session=None):
    result = (_port_get_query(context, session=session)
              .filter_by(id=port_id)
              .first())

    if not result:
        raise exception.PortNotFound(port_id)

    return result


def port_create(context, values):
    """Create a port from the values dictionary."""
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    port_ref = models.Port()
    port_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(port_ref)

    return _port_get(context,
                     port_ref['id'],
                     session=session)


def port_update(context, port_id, values):
    """Update a port with the values dictionary."""
    session = get_session()

    with session.begin():
        query = _port_get_query(context, session)
        result = query.filter_by(id=port_id).update(values)

        if not result:
            raise exception.PortNotFound(port_id)

    return result


def port_get(context, port_id):
    """Get a port or raise an exception if it does not exist."""
    return _port_get(context, port_id)


def port_delete_by_storage(context, storage_id):
    """Delete port or raise an exception if it does not exist."""
    _port_get_query(context).filter_by(storage_id=storage_id).delete()


def port_get_all(context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
    """Retrieves all ports."""

    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.Port,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No Port would match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.Port)
def _process_port_info_filters(query, filters):
    """Common filter processing for ports queries."""
    if filters:
        if not is_valid_model_filters(models.Port, filters):
            return
        query = query.filter_by(**filters)

    return query


def disks_create(context, disks):
    """Create multiple disks."""
    session = get_session()
    disks_refs = []
    with session.begin():

        for disk in disks:
            LOG.debug('adding new disk for native_disk_id {0}:'
                      .format(disk.get('native_disk_id')))
            if not disk.get('id'):
                disk['id'] = uuidutils.generate_uuid()

            disk_ref = models.Disk()
            disk_ref.update(disk)
            disks_refs.append(disk_ref)

        session.add_all(disks_refs)

    return disks_refs


def disks_update(context, disks):
    """Update multiple disks."""
    session = get_session()

    with session.begin():
        disk_refs = []

        for disk in disks:
            LOG.debug('updating disk {0}:'.format(
                disk.get('id')))
            query = _disk_get_query(context, session)
            result = query.filter_by(id=disk.get('id')
                                     ).update(disk)

            if not result:
                LOG.error(exception.DiskNotFound(disk.get(
                    'id')))
            else:
                disk_refs.append(result)

    return disk_refs


def disks_delete(context, disks_id_list):
    """Delete multiple disks."""
    session = get_session()
    with session.begin():
        for disk_id in disks_id_list:
            LOG.debug('deleting disk {0}:'.format(disk_id))
            query = _disk_get_query(context, session)
            result = query.filter_by(id=disk_id).delete()

            if not result:
                LOG.error(exception.DiskNotFound(disk_id))

    return


def _disk_get_query(context, session=None):
    return model_query(context, models.Disk, session=session)


def _disk_get(context, disk_id, session=None):
    result = (_disk_get_query(context, session=session)
              .filter_by(id=disk_id)
              .first())

    if not result:
        raise exception.DiskNotFound(disk_id)

    return result


def disk_create(context, values):
    """Create a disk from the values dictionary."""
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    disk_ref = models.Disk()
    disk_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(disk_ref)

    return _disk_get(context,
                     disk_ref['id'],
                     session=session)


def disk_update(context, disk_id, values):
    """Update a disk with the values dictionary."""
    session = get_session()

    with session.begin():
        query = _disk_get_query(context, session)
        result = query.filter_by(id=disk_id).update(values)

        if not result:
            raise exception.DiskNotFound(disk_id)

    return result


def disk_get(context, disk_id):
    """Get a disk or raise an exception if it does not exist."""
    return _disk_get(context, disk_id)


def disk_delete_by_storage(context, storage_id):
    """Delete disk or raise an exception if it does not exist."""
    _disk_get_query(context).filter_by(storage_id=storage_id).delete()


def disk_get_all(context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
    """Retrieves all disks."""

    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.Disk,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No Disk would match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.Disk)
def _process_disk_info_filters(query, filters):
    """Common filter processing for disks queries."""
    if filters:
        if not is_valid_model_filters(models.Disk, filters):
            return
        query = query.filter_by(**filters)

    return query


def filesystems_create(context, filesystems):
    """Create multiple filesystems."""
    session = get_session()
    filesystems_refs = []
    with session.begin():

        for filesystem in filesystems:
            LOG.debug('adding new filesystem for native_filesystem_id {0}:'
                      .format(filesystem.get('native_filesystem_id')))
            if not filesystem.get('id'):
                filesystem['id'] = uuidutils.generate_uuid()

            filesystem_ref = models.Filesystem()
            filesystem_ref.update(filesystem)
            filesystems_refs.append(filesystem_ref)

        session.add_all(filesystems_refs)

    return filesystems_refs


def filesystems_update(context, filesystems):
    """Update multiple filesystems."""
    session = get_session()

    with session.begin():
        filesystem_refs = []

        for filesystem in filesystems:
            LOG.debug('updating filesystem {0}:'.format(
                filesystem.get('id')))
            query = _filesystem_get_query(context, session)
            result = query.filter_by(id=filesystem.get('id')
                                     ).update(filesystem)

            if not result:
                LOG.error(exception.FilesystemNotFound(filesystem.get(
                    'id')))
            else:
                filesystem_refs.append(result)

    return filesystem_refs


def filesystems_delete(context, filesystems_id_list):
    """Delete multiple filesystems."""
    session = get_session()
    with session.begin():
        for filesystem_id in filesystems_id_list:
            LOG.debug('deleting filesystem {0}:'.format(filesystem_id))
            query = _filesystem_get_query(context, session)
            result = query.filter_by(id=filesystem_id).delete()

            if not result:
                LOG.error(exception.FilesystemNotFound(filesystem_id))
    return


def _filesystem_get_query(context, session=None):
    return model_query(context, models.Filesystem, session=session)


def _filesystem_get(context, filesystem_id, session=None):
    result = (_filesystem_get_query(context, session=session)
              .filter_by(id=filesystem_id)
              .first())

    if not result:
        raise exception.FilesystemNotFound(filesystem_id)

    return result


def filesystem_create(context, values):
    """Create a filesystem from the values dictionary."""
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    filesystem_ref = models.Filesystem()
    filesystem_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(filesystem_ref)

    return _filesystem_get(context,
                           filesystem_ref['id'],
                           session=session)


def filesystem_update(context, filesystem_id, values):
    """Update a filesystem with the values dictionary."""
    session = get_session()

    with session.begin():
        query = _filesystem_get_query(context, session)
        result = query.filter_by(id=filesystem_id).update(values)

        if not result:
            raise exception.FilesystemNotFound(filesystem_id)

    return result


def filesystem_get(context, filesystem_id):
    """Get a filesystem or raise an exception if it does not exist."""
    return _filesystem_get(context, filesystem_id)


def filesystem_delete_by_storage(context, storage_id):
    """Delete filesystem or raise an exception if it does not exist."""
    _filesystem_get_query(context).filter_by(storage_id=storage_id).delete()


def filesystem_get_all(context, marker=None, limit=None, sort_keys=None,
                       sort_dirs=None, filters=None, offset=None):
    """Retrieves all filesystems."""

    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.Filesystem,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No Filesystem would match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.Filesystem)
def _process_filesystem_info_filters(query, filters):
    """Common filter processing for filesystems queries."""
    if filters:
        if not is_valid_model_filters(models.Filesystem, filters):
            return
        query = query.filter_by(**filters)

    return query


def quotas_create(context, quotas):
    """Create multiple quotas."""
    session = get_session()
    quotas_refs = []
    with session.begin():

        for quota in quotas:
            LOG.debug('adding new quota for native_quota_id {0}:'
                      .format(quota.get('native_quota_id')))
            if not quota.get('id'):
                quota['id'] = uuidutils.generate_uuid()

            quota_ref = models.Quota()
            quota_ref.update(quota)
            quotas_refs.append(quota_ref)

        session.add_all(quotas_refs)

    return quotas_refs


def quotas_update(context, quotas):
    """Update multiple quotas."""
    session = get_session()

    with session.begin():
        quota_refs = []

        for quota in quotas:
            LOG.debug('updating quota {0}:'.format(
                quota.get('id')))
            query = _quota_get_query(context, session)
            result = query.filter_by(id=quota.get('id')
                                     ).update(quota)

            if not result:
                LOG.error(exception.QuotaNotFound(quota.get(
                    'id')))
            else:
                quota_refs.append(result)

    return quota_refs


def quotas_delete(context, quotas_id_list):
    """Delete multiple quotas."""
    session = get_session()
    with session.begin():
        for quota_id in quotas_id_list:
            LOG.debug('deleting quota {0}:'.format(quota_id))
            query = _quota_get_query(context, session)
            result = query.filter_by(id=quota_id).delete()

            if not result:
                LOG.error(exception.QuotaNotFound(quota_id))
    return


def _quota_get_query(context, session=None):
    return model_query(context, models.Quota, session=session)


def _quota_get(context, quota_id, session=None):
    result = (_quota_get_query(context, session=session)
              .filter_by(id=quota_id)
              .first())

    if not result:
        raise exception.QuotaNotFound(quota_id)

    return result


def quota_create(context, values):
    """Create a quota from the values dictionary."""
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    quota_ref = models.Quota()
    quota_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(quota_ref)

    return _quota_get(context,
                      quota_ref['id'],
                      session=session)


def quota_update(context, quota_id, values):
    """Update a quota with the values dictionary."""
    session = get_session()

    with session.begin():
        query = _quota_get_query(context, session)
        result = query.filter_by(id=quota_id).update(values)

        if not result:
            raise exception.QuotaNotFound(quota_id)

    return result


def quota_get(context, quota_id):
    """Get a quota or raise an exception if it does not exist."""
    return _quota_get(context, quota_id)


def quota_delete_by_storage(context, storage_id):
    """Delete quota or raise an exception if it does not exist."""
    _quota_get_query(context).filter_by(storage_id=storage_id).delete()


def quota_get_all(context, marker=None, limit=None, sort_keys=None,
                  sort_dirs=None, filters=None, offset=None):
    """Retrieves all quotas."""

    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.Quota,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No Quota would match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.Quota)
def _process_quota_info_filters(query, filters):
    """Common filter processing for quotas queries."""
    if filters:
        if not is_valid_model_filters(models.Quota, filters):
            return
        query = query.filter_by(**filters)

    return query


def qtrees_create(context, qtrees):
    """Create multiple qtrees."""
    session = get_session()
    qtrees_refs = []
    with session.begin():

        for qtree in qtrees:
            LOG.debug('adding new qtree for native_qtree_id {0}:'
                      .format(qtree.get('native_qtree_id')))
            if not qtree.get('id'):
                qtree['id'] = uuidutils.generate_uuid()

            qtree_ref = models.Qtree()
            qtree_ref.update(qtree)
            qtrees_refs.append(qtree_ref)

        session.add_all(qtrees_refs)

    return qtrees_refs


def qtrees_update(context, qtrees):
    """Update multiple qtrees."""
    session = get_session()

    with session.begin():
        qtree_refs = []

        for qtree in qtrees:
            LOG.debug('updating qtree {0}:'.format(
                qtree.get('id')))
            query = _qtree_get_query(context, session)
            result = query.filter_by(id=qtree.get('id')
                                     ).update(qtree)

            if not result:
                LOG.error(exception.QtreeNotFound(qtree.get(
                    'id')))
            else:
                qtree_refs.append(result)

    return qtree_refs


def qtrees_delete(context, qtrees_id_list):
    """Delete multiple qtrees."""
    session = get_session()
    with session.begin():
        for qtree_id in qtrees_id_list:
            LOG.debug('deleting qtree {0}:'.format(qtree_id))
            query = _qtree_get_query(context, session)
            result = query.filter_by(id=qtree_id).delete()

            if not result:
                LOG.error(exception.QtreeNotFound(qtree_id))
    return


def _qtree_get_query(context, session=None):
    return model_query(context, models.Qtree, session=session)


def _qtree_get(context, qtree_id, session=None):
    result = (_qtree_get_query(context, session=session)
              .filter_by(id=qtree_id)
              .first())

    if not result:
        raise exception.QtreeNotFound(qtree_id)

    return result


def qtree_create(context, values):
    """Create a qtree from the values dictionary."""
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    qtree_ref = models.Qtree()
    qtree_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(qtree_ref)

    return _qtree_get(context,
                      qtree_ref['id'],
                      session=session)


def qtree_update(context, qtree_id, values):
    """Update a qtree with the values dictionary."""
    session = get_session()

    with session.begin():
        query = _qtree_get_query(context, session)
        result = query.filter_by(id=qtree_id).update(values)

        if not result:
            raise exception.QtreeNotFound(qtree_id)

    return result


def qtree_get(context, qtree_id):
    """Get a qtree or raise an exception if it does not exist."""
    return _qtree_get(context, qtree_id)


def qtree_delete_by_storage(context, storage_id):
    """Delete qtree or raise an exception if it does not exist."""
    _qtree_get_query(context).filter_by(storage_id=storage_id).delete()


def qtree_get_all(context, marker=None, limit=None, sort_keys=None,
                  sort_dirs=None, filters=None, offset=None):
    """Retrieves all qtrees."""

    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.Qtree,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No Qtree would match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.Qtree)
def _process_qtree_info_filters(query, filters):
    """Common filter processing for qtrees queries."""
    if filters:
        if not is_valid_model_filters(models.Qtree, filters):
            return
        query = query.filter_by(**filters)

    return query


def shares_create(context, shares):
    """Create multiple shares."""
    session = get_session()
    shares_refs = []
    with session.begin():

        for share in shares:
            LOG.debug('adding new share for native_share_id {0}:'
                      .format(share.get('native_share_id')))
            if not share.get('id'):
                share['id'] = uuidutils.generate_uuid()

            share_ref = models.Share()
            share_ref.update(share)
            shares_refs.append(share_ref)

        session.add_all(shares_refs)

    return shares_refs


def shares_update(context, shares):
    """Update multiple shares."""
    session = get_session()

    with session.begin():
        share_refs = []

        for share in shares:
            LOG.debug('updating share {0}:'.format(
                share.get('id')))
            query = _share_get_query(context, session)
            result = query.filter_by(id=share.get('id')
                                     ).update(share)

            if not result:
                LOG.error(exception.ShareNotFound(share.get(
                    'id')))
            else:
                share_refs.append(result)

    return share_refs


def shares_delete(context, shares_id_list):
    """Delete multiple shares."""
    session = get_session()
    with session.begin():
        for share_id in shares_id_list:
            LOG.debug('deleting share {0}:'.format(share_id))
            query = _share_get_query(context, session)
            result = query.filter_by(id=share_id).delete()

            if not result:
                LOG.error(exception.ShareNotFound(share_id))
    return


def _share_get_query(context, session=None):
    return model_query(context, models.Share, session=session)


def _share_get(context, share_id, session=None):
    result = (_share_get_query(context, session=session)
              .filter_by(id=share_id)
              .first())

    if not result:
        raise exception.ShareNotFound(share_id)

    return result


def share_create(context, values):
    """Create a share from the values dictionary."""
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    share_ref = models.Share()
    share_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(share_ref)

    return _share_get(context,
                      share_ref['id'],
                      session=session)


def share_update(context, share_id, values):
    """Update a share with the values dictionary."""
    session = get_session()

    with session.begin():
        query = _share_get_query(context, session)
        result = query.filter_by(id=share_id).update(values)

        if not result:
            raise exception.ShareNotFound(share_id)

    return result


def share_get(context, share_id):
    """Get a share or raise an exception if it does not exist."""
    return _share_get(context, share_id)


def share_delete_by_storage(context, storage_id):
    """Delete share or raise an exception if it does not exist."""
    _share_get_query(context).filter_by(storage_id=storage_id).delete()


def share_get_all(context, marker=None, limit=None, sort_keys=None,
                  sort_dirs=None, filters=None, offset=None):
    """Retrieves all shares."""

    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.Share,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No Share would match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.Share)
def _process_share_info_filters(query, filters):
    """Common filter processing for shares queries."""
    if filters:
        if not is_valid_model_filters(models.Share, filters):
            return
        query = query.filter_by(**filters)

    return query


def is_orm_value(obj):
    """Check if object is an ORM field or expression."""
    return isinstance(obj, (sqlalchemy.orm.attributes.InstrumentedAttribute,
                            sqlalchemy.sql.expression.ColumnElement))


def model_query(context, model, *args, **kwargs):
    """Query helper for model query.

    :param context: context to query under
    :param model: model to query. Must be a subclass of ModelBase.
    :param session: if present, the session to use
    """
    session = kwargs.pop('session') or get_session()
    return db_utils.model_query(
        model=model, session=session, args=args, **kwargs)


def alert_source_get(context, storage_id):
    """Get an alert source or raise an exception if it does not exist."""
    return _alert_source_get(context, storage_id)


def _alert_source_get(context, storage_id, session=None):
    result = (_alert_source_get_query(context, session=session)
              .filter_by(storage_id=storage_id)
              .first())

    if not result:
        raise exception.AlertSourceNotFound(storage_id)

    return result


def _alert_source_get_query(context, session=None):
    return model_query(context, models.AlertSource, session=session)


@apply_like_filters(model=models.AlertSource)
def _process_alert_source_filters(query, filters):
    """Common filter processing for alert source queries."""
    if filters:
        if not is_valid_model_filters(models.AlertSource, filters):
            return
        query = query.filter_by(**filters)

    return query


def alert_source_create(context, values):
    """Add an alert source configuration."""
    alert_source_ref = models.AlertSource()
    alert_source_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(alert_source_ref)

    return _alert_source_get(context,
                             alert_source_ref['storage_id'],
                             session=session)


def alert_source_update(context, storage_id, values):
    """Update an alert source configuration."""
    session = get_session()
    with session.begin():
        _alert_source_get(context, storage_id, session).update(values)
        return _alert_source_get(context, storage_id, session)


def alert_source_delete(context, storage_id):
    session = get_session()
    with session.begin():
        query = _alert_source_get_query(context, session)
        result = query.filter_by(storage_id=storage_id).delete()
        if not result:
            LOG.error("Cannot delete non-exist alert source[storage_id=%s]." %
                      storage_id)
            raise exception.AlertSourceNotFound(storage_id)
        else:
            LOG.info("Delete alert source[storage_id=%s] successfully." %
                     storage_id)


def alert_source_get_all(context, marker=None, limit=None, sort_keys=None,
                         sort_dirs=None, filters=None, offset=None):
    session = get_session()
    with session.begin():
        query = _generate_paginate_query(context, session, models.AlertSource,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset)
        if query is None:
            return []
        return query.all()


def task_create(context, values):
    """Add task configuration."""
    tasks_ref = models.Task()
    tasks_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(tasks_ref)

    return _task_get(context, tasks_ref['id'], session=session)


def task_update(context, tasks_id, values):
    """Update a task attributes withe the values dictionary."""
    session = get_session()

    with session.begin():
        query = _task_get_query(context, session)
        result = query.filter_by(id=tasks_id).update(values)

        if not result:
            raise exception.TaskNotFound(tasks_id)

    return result


def _task_get(context, task_id, session=None):
    result = (_task_get_query(context, session=session)
              .filter_by(id=task_id)
              .first())

    if not result:
        raise exception.TaskNotFound(task_id)

    return result


def _task_get_query(context, session=None):
    return model_query(context, models.Task, session=session)


def task_get(context, tasks_id):
    """Get a task  or raise an exception if it does not exist."""
    return _task_get(context, tasks_id)


def task_delete_by_storage(context, storage_id):
    """Delete all the tasks of a storage device"""
    delete_info = {'deleted': True, 'deleted_at': timeutils.utcnow()}
    _task_get_query(context).filter_by(
        storage_id=storage_id).update(delete_info)


def task_delete(context, tasks_id):
    """Delete a given task"""
    _task_get_query(context).filter_by(id=tasks_id).delete()


def task_get_all(context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
    """Retrieves all tasks of a storage."""
    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.Task,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No task entry would match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.Task)
def _process_tasks_info_filters(query, filters):
    """Common filter processing for task table queries."""
    if filters:
        if not is_valid_model_filters(models.Task, filters):
            return
        query = query.filter_by(**filters)

    return query


def failed_task_create(context, values):
    """Add failed task configuration."""
    failed_task_ref = models.FailedTask()
    failed_task_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(failed_task_ref)

    return _failed_tasks_get(context, failed_task_ref['id'], session=session)


def failed_task_update(context, failed_task_id, values):
    """Update a failed task withe the values dictionary."""
    session = get_session()

    with session.begin():
        query = _failed_tasks_get_query(context, session)
        result = query.filter_by(id=failed_task_id).update(values)

        if not result:
            raise exception.FailedTaskNotFound(failed_task_id)

    return result


def _failed_tasks_get(context, failed_task_id, session=None):
    result = (_failed_tasks_get_query(context, session=session)
              .filter_by(id=failed_task_id)
              .first())

    if not result:
        raise exception.FailedTaskNotFound(failed_task_id)

    return result


def _failed_tasks_get_query(context, session=None):
    return model_query(context, models.FailedTask, session=session)


def failed_task_get(context, failed_task_id):
    """Get a failed task or raise an exception if it does not exist."""
    return _failed_tasks_get(context, failed_task_id)


def failed_task_delete_by_task_id(context, task_id):
    """Delete all the failed tasks of a given task id"""
    _failed_tasks_get_query(context).filter_by(
        task_id=task_id).delete()


def failed_task_delete_by_storage(context, storage_id):
    """Delete all the failed tasks of a storage device"""
    delete_info = {'deleted': True, 'deleted_at': timeutils.utcnow()}
    _failed_tasks_get_query(context).filter_by(
        storage_id=storage_id).update(delete_info)


def failed_task_delete(context, failed_task_id):
    """Delete a given failed task"""
    _failed_tasks_get_query(context).filter_by(id=failed_task_id).delete()


def failed_task_get_all(context, marker=None, limit=None, sort_keys=None,
                        sort_dirs=None, filters=None, offset=None):
    """Retrieves all failed tasks."""
    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, models.FailedTask,
                                         marker, limit, sort_keys, sort_dirs,
                                         filters, offset,
                                         )
        # No failed task would match, return empty list
        if query is None:
            return []
        return query.all()


@apply_like_filters(model=models.FailedTask)
def _process_failed_tasks_info_filters(query, filters):
    """Common filter processing for failed task queries."""
    if filters:
        if not is_valid_model_filters(models.FailedTask, filters):
            return
        query = query.filter_by(**filters)

    return query


PAGINATION_HELPERS = {
    models.AccessInfo: (_access_info_get_query, _process_access_info_filters,
                        _access_info_get),
    models.StoragePool: (_storage_pool_get_query,
                         _process_storage_pool_info_filters,
                         _storage_pool_get),
    models.Storage: (_storage_get_query, _process_storage_info_filters,
                     _storage_get),
    models.CentralizedManager: (_centralized_manager_get_query,
                                _process_centralized_manager_info_filters,
                                _centralized_manager_get),
    models.AlertSource: (_alert_source_get_query,
                         _process_alert_source_filters,
                         _alert_source_get),
    models.Volume: (_volume_get_query, _process_volume_info_filters,
                    _volume_get),
    models.Controller: (_controller_get_query,
                        _process_controller_info_filters,
                        _controller_get),
    models.Port: (_port_get_query, _process_port_info_filters, _port_get),
    models.Disk: (_disk_get_query, _process_disk_info_filters,
                  _disk_get),
    models.Quota: (_quota_get_query,
                   _process_quota_info_filters, _quota_get),
    models.Filesystem: (_filesystem_get_query,
                        _process_filesystem_info_filters, _filesystem_get),
    models.Qtree: (_qtree_get_query,
                   _process_qtree_info_filters, _qtree_get),
    models.Share: (_share_get_query,
                   _process_share_info_filters, _share_get),
    models.Task: (_task_get_query,
                  _process_tasks_info_filters,
                  _task_get),
    models.FailedTask: (_failed_tasks_get_query,
                        _process_failed_tasks_info_filters,
                        _failed_tasks_get),
}


def process_sort_params(sort_keys, sort_dirs, default_keys=None,
                        default_dir='asc'):
    """Process the sort parameters to include default keys.

    Creates a list of sort keys and a list of sort directions. Adds the default
    keys to the end of the list if they are not already included.

    When adding the default keys to the sort keys list, the associated
    direction is:
    1) The first element in the 'sort_dirs' list (if specified), else
    2) 'default_dir' value (Note that 'asc' is the default value since this is
    the default in sqlalchemy.utils.paginate_query)

    :param sort_keys: List of sort keys to include in the processed list
    :param sort_dirs: List of sort directions to include in the processed list
    :param default_keys: List of sort keys that need to be included in the
                         processed list, they are added at the end of the list
                         if not already specified.
    :param default_dir: Sort direction associated with each of the default
                        keys that are not supplied, used when they are added
                        to the processed list
    :returns: list of sort keys, list of sort directions
    :raise exception.InvalidInput: If more sort directions than sort keys
                                   are specified or if an invalid sort
                                   direction is specified
    """
    if default_keys is None:
        default_keys = ['created_at']

    # Determine direction to use for when adding default keys
    if sort_dirs and len(sort_dirs):
        default_dir_value = sort_dirs[0]
    else:
        default_dir_value = default_dir

    # Create list of keys (do not modify the input list)
    if sort_keys:
        result_keys = list(sort_keys)
    else:
        result_keys = []

    # If a list of directions is not provided, use the default sort direction
    # for all provided keys.
    if sort_dirs:
        result_dirs = []
        # Verify sort direction
        for sort_dir in sort_dirs:
            if sort_dir not in ('asc', 'desc'):
                msg = _("Unknown sort direction, must be 'desc' or 'asc'.")
                raise exception.InvalidInput(msg)
            result_dirs.append(sort_dir)
    else:
        result_dirs = [default_dir_value for _sort_key in result_keys]

    # Ensure that the key and direction length match
    while len(result_dirs) < len(result_keys):
        result_dirs.append(default_dir_value)
    # Unless more direction are specified, which is an error
    if len(result_dirs) > len(result_keys):
        msg = _("Sort direction array size exceeds sort key array size.")
        raise exception.InvalidInput(msg)

    # Ensure defaults are included
    for key in default_keys:
        if key not in result_keys:
            result_keys.append(key)
            result_dirs.append(default_dir_value)

    return result_keys, result_dirs


def _generate_paginate_query(context, session, paginate_type, marker,
                             limit, sort_keys, sort_dirs, filters,
                             offset=None
                             ):
    """Generate the query to include the filters and the paginate options.

    Returns a query with sorting / pagination criteria added or None
    if the given filters will not yield any results.

    :param context: context to query under
    :param session: the session to use
    :param marker: the last item of the previous page; we returns the next
                    results after this value.
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys
    :param filters: dictionary of filters; values that are in lists, tuples,
                    or sets cause an 'IN' operation, while exact matching
                    is used for other values, see _process_volume_filters
                    function for more information
    :param offset: number of items to skip
    :param paginate_type: type of pagination to generate
    :returns: updated query or None
    """
    get_query, process_filters, get = PAGINATION_HELPERS[paginate_type]

    sort_keys, sort_dirs = process_sort_params(sort_keys,
                                               sort_dirs,
                                               default_dir='desc')
    query = get_query(context, session=session)

    if filters:
        query = process_filters(query, filters)
        if query is None:
            return None

    marker_object = None
    if marker is not None:
        marker_object = get(context, marker, session)

    return sqlalchemyutils.paginate_query(query, paginate_type, limit,
                                          sort_keys,
                                          marker=marker_object,
                                          sort_dirs=sort_dirs,
                                          offset=offset)
