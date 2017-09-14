# Copyright 2017 Canonical Limited.
#
# This file is part of charms.reactive.
#
# charms.reactive is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charms.reactive is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

from charmhelpers.core import hookenv
from charms.reactive import set_flag, toggle_flag
from charms.reactive.flags import _get_flag_value
from charms.reactive.helpers import data_changed, context
from charms.reactive.relations import RelationFactory, relation_factory


class MinimalRelationBase(RelationFactory):
    def __init__(self, relation_name):
        self.relation_name = relation_name

    def set_state(self, state):
        """
        Set state, tied to this relation.

        Usage:

            @hook('{requires:my-interface}-relation-{joined,changed}')
            def changed(self):
                self.set_state('{relation_name}.available')
        """
        set_flag(
            state.format(relation_name=self.relation_name),
            {'relation': self.relation_name})

    @classmethod
    def from_name(cls, relation_name):
        return cls(relation_name)

    @classmethod
    def from_flag(cls, flag):
        value = _get_flag_value(flag)
        if value is None:
            return None
        relation_name = value['relation']
        return cls.from_name(relation_name)


class Endpoint(RelationFactory):
    @classmethod
    def _startup(cls):
        for endpoint in hookenv.relation_types():
            rids = hookenv.relation_ids(endpoint)

            # populate context based on attached relations
            relf = relation_factory(endpoint)
            if issubclass(relf, cls):
                if rids:
                    rel = relf(endpoint)
                    setattr(context.endpoints, endpoint, rel)
                else:
                    setattr(context.endpoints, endpoint, None)

            # manage automatic relation flags
            toggle_flag('relations.{}.joined'.format(endpoint), rids)
            for rid in rids:
                for unit in hookenv.related_units(rid):
                    rel_data = hookenv.relation_get(unit=unit, rid=rid)
                    for key, value in rel_data.items():
                        data_key = 'relations.{}.{}.{}.{}'.format(
                            endpoint, rid, unit, key)
                        if data_changed(data_key, value):
                            set_flag('relations.{}.changed'.format(endpoint))
                            set_flag('relations.{}.changed.{}'.format(
                                endpoint, key))

    def __init__(self, relation_name):
        self.relation_name = relation_name

    def set_flag(self, flag):
        """
        Set flag, tied to this relation.

        Usage:

            @when('relations.{relation_name}.changed')
            def changed(self):
                if any('host' in unit.receive for unit in self.units):
                    self.set_flag('relations.{relation_name}.available')
        """
        set_flag(flag.format(relation_name=self.relation_name))

    @classmethod
    def from_name(cls, relation_name):
        return cls(relation_name)

    @classmethod
    def from_flag(cls, flag):
        parts = flag.split('.')
        if len(parts) < 3 or parts[0] != 'relations':
            return None
        return cls.from_name(parts[1])


hookenv.atstart(Endpoint._startup)
