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
from delfin import db
from delfin import cryptor
from delfin.api import validation
from delfin.api.common import wsgi
from delfin.api.schemas import access_info as schema_access_info
from delfin.api.views import access_info as access_info_viewer
from delfin.common import constants
from delfin.drivers import api as driverapi


class AccessInfoController(wsgi.Controller):

    def __init__(self):
        super(AccessInfoController, self).__init__()
        self._view_builder = access_info_viewer.ViewBuilder()
        self.driver_api = driverapi.API()

    def show(self, req, id):
        """Show access information by storage id."""
        ctxt = req.environ['delfin.context']
        access_info = db.access_info_get(ctxt, id)
        return self._view_builder.show(access_info)

    @validation.schema(schema_access_info.update)
    def update(self, req, id, body):
        """Update storage access information."""
        ctxt = req.environ.get('delfin.context')
        access_info = db.access_info_get(ctxt, id)
        for access in constants.ACCESS_TYPE:
            if access_info.get(access):
                access_info[access]['password'] = cryptor.decode(
                    access_info[access]['password'])
            if body.get(access):
                access_info[access].update(body[access])
        access_info = self.driver_api.update_access_info(ctxt, access_info)
        return self._view_builder.show(access_info)

    @validation.schema(schema_access_info.update)
    def update_cm(self, req, id, body):
        """Update cm access information."""
        ctxt = req.environ.get('delfin.context')
        access_info = db.access_info_get(ctxt, id)
        for access in constants.ACCESS_TYPE:
            if access_info.get(access):
                access_info[access]['password'] = cryptor.decode(
                    access_info[access]['password'])
            if body.get(access):
                access_info[access].update(body[access])
        access_info = self.driver_api.update_cm_access_info(ctxt, access_info)
        return self._view_builder.show(access_info)


def create_resource():
    return wsgi.Resource(AccessInfoController())
