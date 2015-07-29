# Copyright 2014-2015 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

from charms.reactive import RelationBase
from charms.reactive import scopes
from charms.reactive import hook
from charms.reactive import when


class TestRelation(RelationBase):
    scope = scopes.GLOBAL

    @hook('{requires:test}-relation-joined')
    def joined(self):
        self.set_state('{relation_name}.ready')

    @when('test-rel.ready')
    def test(self):
        self.set_local('call_count', self.get_local('call_count', 0) + 1)
        self.set_state('relation')
