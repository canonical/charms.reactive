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

from charms.reactive import get_state, set_state
from charms.reactive.relations import RelationFactory


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
        set_state(
            state.format(relation_name=self.relation_name),
            {'relation': self.relation_name})

    @classmethod
    def from_name(cls, relation_name):
        return cls(relation_name)

    @classmethod
    def from_state(cls, state):
        value = get_state(state)
        if value is None:
            return None
        relation_name = value['relation']
        return cls.from_name(relation_name)
