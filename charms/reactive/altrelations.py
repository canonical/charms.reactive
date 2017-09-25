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

import json
import weakref
from collections import UserDict
from itertools import chain

from charmhelpers.core import hookenv
from charms.reactive.flags import _get_flag_value
from charms.reactive.flags import set_flag, toggle_flag, is_flag_set
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
    def from_name(cls, relation_name):
        return getattr(context.endpoints, relation_name, None)

    @classmethod
    def from_flag(cls, flag):
        if '.' not in flag:
            return None
        parts = flag.split('.')
        if parts[0] == 'endpoint':
            return cls.from_name(parts[1])
        else:
            # some older handlers might not use the 'endpoint' prefix
            return cls.from_name(parts[0])

    @classmethod
    def _startup(cls):
        """
        Populate context and manage automatic relation flags.
        """
        for relation_name in sorted(hookenv.relation_types()):
            # populate context based on attached relations
            relf = relation_factory(relation_name)
            if not issubclass(relf, cls):
                continue

            rids = sorted(hookenv.relation_ids(relation_name))
            endpoint = relf(relation_name, rids)
            setattr(context.endpoints, relation_name, endpoint)
            endpoint._manage_flags()
            for relation in endpoint.relations:
                hookenv.atexit(relation._flush_data)

    def __init__(self, relation_name, relation_ids=None):
        self._relation_name = relation_name
        self._relations = KeyList(map(Relation, relation_ids or []),
                                  key='relation_id')
        self._all_units = None

    @property
    def relation_name(self):
        """
        Relation name of this endpoint.
        """
        return self._relation_name

    @property
    def relations(self):
        """
        Collection of `Relation`s that are established for this `Endpoint`.

        This is a `KeyList`, so it can be iterated and indexed as a list,
        or you can look up relations by their ID.  For example::

            rel0 = endpoint.relations[0]
            assert rel0 is endpoint.relations[rel0.relation_id]
            assert all(rel is endpoint.relations[rel.relation_id]
                       for rel in endpoint.relations)
            print(', '.join(endpoint.relations.keys()))
        """
        return self._relations

    @property
    def joined(self):
        """
        Whether this endpoint has remote applications attached to it.
        """
        return len(self.relations) > 0

    def flag(self, flag):
        """
        Complete a flag name for this endpoint.

        If the flag does not already contain ``{relation_name}``, it will be
        prefixed with ``endpoint.{relation_name}.``. Then, ``str.format`` will
        be used to fill in ``{relation_name}`` with ``self.relation_name``.
        """
        if '{relation_name}' not in flag:
            flag = 'endpoint.{relation_name}.' + flag
        return flag.format(relation_name=self.relation_name)

    def _manage_flags(self):
        """
        Manage automatic relation flags.
        """
        already_joined = is_flag_set(self.flag('joined'))
        hook_name = hookenv.hook_name()
        rel_hook = hook_name.startswith(self.relation_name + '-relation-')
        departed_hook = rel_hook and hook_name.endswith('-departed')

        toggle_flag(self.flag('joined'), self.joined)
        toggle_flag(self.flag('departed'), departed_hook)

        if already_joined and not rel_hook:
            # skip checking relation data outside hooks for this relation
            # to save on API calls to the controller (unless we didn't have
            # the joined flag before, since then we might migrating to Endpoints)
            return

        for unit in self.all_units:
            for key, value in unit.received.items():
                data_key = 'endpoint.{}.{}.{}.{}'.format(self.relation_name,
                                                         unit.relation.relation_name,
                                                         unit.unit_name,
                                                         key)
                if data_changed(data_key, value):
                    toggle_flag(self.flag('changed'), True)
                    toggle_flag(self.flag('changed.{}'.format(key)), True)

    @property
    def all_units(self):
        """
        A list view of all the units attached to this `Endpoint`, across all relations.

        This is actually a `CombinedUnitsView`, so the units will be in order by
        relation ID and then unit name, and you can access a merged view of all
        the units' data as a single mapping.  You should be very careful when
        using the merged data collections, however, and consider carefully
        what will happen when the endpoint has multiple relations and multiple
        remote units on each.  It is probably better to iterate over each unit
        and handle its data individually.  See `CombinedUnitsView` for an
        explanation of how the merged data collections work.

        Note that, because a given application might be related multiple times
        on a given endpoint, units may show up in this collection more than once.
        """
        if self._all_units is None:
            units = chain.from_iterable(rel.units for rel in self.relations)
            self._all_units = CombinedUnitsView(units)
        return self._all_units


class Relation:
    def __init__(self, relation_id):
        self._relation_id = relation_id
        self._relation_name = relation_id.split(':')[0]
        self._application_name = None
        self._units = None
        self._data = None

    @property
    def relation_id(self):
        """
        This relation's relation ID.
        """
        return self._relation_id

    @property
    def relation_name(self):
        """
        This relation's relation name.

        This will be the same as the `Endpoint`'s relation name.
        """
        return self._relation_name

    @property
    def application_name(self):
        """
        The name of the remote application for this relation, or ``None``.

        This is equivalent to::

            relation.units[0].unit_name.split('/')[0]
        """
        if self._application_name is None and self.units:
            self._application_name = self.units[0].unit_name.split('/')[0]
        return self._application_name

    @property
    def units(self):
        """
        A list view of all the units on this relation.

        This is actually a `CombinedUnitsView`, so the units will be in order
        by unit name, and you can access a merged view of all of the units'
        data with ``self.units.received`` and ``self.units.received_json``.
        You should be very careful when using the merged data collections,
        however, and consider carefully what will happen when there are
        multiple remote units.  It is probabaly better to iterate over each
        unit and handle its data individually.  See `CombinedUnitsView` for
        an explanation of how the merged data collections work.

        The view can be iterated and indexed as a list, or you can look up
        units by their unit name.  For example::

            by_index = relation.units[0]
            by_name = relation.units['unit/0']
            assert by_index is by_name
            assert all(unit is relation.units[unit.unit_name]
                       for unit in relation.units)
            print(', '.join(relation.units.keys()))
        """
        if self._units is None:
            self._units = CombinedUnitsView([
                RelatedUnit(self, unit_name) for unit_name in
                sorted(hookenv.related_units(self.relation_id))
            ])
        return self._units

    @property
    def send_json(self):
        """
        Returns a writeable `JSONUnitDataView` of this local unit's data
        on this relation.

        Data stored in this collection will be automatically JSON encoded.
        Mappings stored in this collection will be encoded with sorted keys,
        to ensure that the encoded representation will only change if the
        actual data changes.

        Changes to this unit's relation data are sent out at the end of
        the current hook.
        """
        if self._data is None:
            self._data = JSONUnitDataView(
                hookenv.relation_get(unit=hookenv.local_unit(),
                                     rid=self.relation_id),
                writeable=True)
        return self._data

    @property
    def send(self):
        """
        Returns a writeable `UnitDataView` of this local unit's data
        on this relation.

        Changes to this unit's relation data are sent out at the end of
        the current hook.
        """
        return self.send_json.data

    def _flush_data(self):
        """
        If this relation's local unit data has been modified, send it out
        over the relation.  This should be automatically called.
        """
        if self._data and self._data.modified:
            hookenv.relation_set(self.relation_id, dict(self.send_json.data))


class RelatedUnit:
    """
    Class representing a remote unit on a relation.
    """
    def __init__(self, relation, unit_name):
        self._relation = weakref.ref(relation)
        self.unit_name = unit_name
        self.application_name = unit_name.split('/')[0]
        self._data = None

    @property
    def relation(self):
        """
        The relation to which this unit belongs.

        To prevent circular references, the relation is kept as a weakref.
        If the relation is garbage-collected before this property is accessed,
        it will be ``None``.
        """
        return self._relation()

    @property
    def received_json(self):
        """
        A `JSONUnitDataView` of the data received from this remote unit over
        the relation, with values being automatically decoded as JSON.
        """
        if self._data is None:
            self._data = JSONUnitDataView(hookenv.relation_get(
                unit=self.unit_name,
                rid=self.relation.relation_id))
        return self._data

    @property
    def received(self):
        """
        A `UnitDataView` of the data received from this remote unit over
        the relation.
        """
        return self.received_json.data


class KeyList(list):
    """
    List that also allows accessing items keyed by an attribute on the items.

    Unlike dicts, the keys don't need to be unique.
    """
    def __init__(self, items, key):
        super().__init__(items)
        self._key = key

    def __getitem__(self, key):
        """
        Access an item in this `KeyList` by either an integer index or a str key.

        If an integer key is given, it will be used as a list index.

        If a str is given, it will be used as a mapping key.  Since keys may not
        be unique, only the first item matching the given key will be returned.
        """
        if isinstance(key, int):
            return super().__getitem__(key)
        for item in self:
            if getattr(item, self._key) == key:
                return item
        raise KeyError(key)

    def keys(self):
        """
        Return the keys for all items in this `KeyList`.

        Unlike a dict, the keys are not necessarily unique, so this list may
        contain duplicate values.  The keys will be returned in the order of
        the items in the list.
        """
        return [getattr(item, self._key) for item in self]

    def values(self):
        """
        Return just the values of this list.

        This is equivalent to ``list(keylist)``.
        """
        return list(self)


class CombinedUnitsView(KeyList):
    """
    A `KeyList` view of `RelatedUnit`s, with properties to access a merged view
    of all of the units' data.

    You can iterate over this view like any other list, or you can look up units
    by their ``unit_name``.  Units will be in order by relation ID and unit name.
    If a given unit name occurs more than once, accessing it by ``unit_name`` will
    return the one from the lowest relation ID::

        # given the following relations...
        {
            'endpoint:1': {
                'unit/1': {
                    'key0': 'value0_1_1',
                    'key1': 'value1_1_1',
                },
                'unit/0': {
                    'key0': 'value0_1_0',
                    'key1': 'value1_1_0',
                },
            },
            'endpoint:0': {
                'unit/1': {
                    'key0': 'value0_0_1',
                    'key2': 'value2_0_1',
                },
            },
        }

        from_all = endpoint.all_units['unit/1']
        by_rel = endpoint.relations['endpoint:0'].units['unit/1']
        by_index = endpoint.relations[0].units[1]
        assert from_all is by_rel
        assert by_rel is by_index

    You can also use the `received` or `received_json` properties just like you
    would on a single unit.  The data in these collections will have all of the
    data from every unit, with units with the lowest relation ID and unit name
    taking precedence if multiple units have set a given field.  For example::

        # given the same relations as above...

        # the values across all relations would be:
        assert endpoint.all_units.received['key0'] == 'value0_0_0'
        assert endpoint.all_units.received['key1'] == 'value1_1_0'
        assert endpoint.all_units.received['key2'] == 'value2_0_1'

        # across individual relations:
        assert endpoint.relations[0].units.received['key0'] == 'value0_0_1'
        assert endpoint.relations[0].units.received['key1'] == None
        assert endpoint.relations[0].units.received['key2'] == 'value2_0_1'
        assert endpoint.relations[1].units.received['key0'] == 'value0_1_0'
        assert endpoint.relations[1].units.received['key1'] == 'value1_1_0'
        assert endpoint.relations[1].units.received['key2'] == None

        # and of course you an access them by individual unit
        assert endpoint.relations['endpoint:1'].units['unit/1'].received['key0'] \
                == 'value0_1_1'

    """
    def __init__(self, items):
        super().__init__(sorted(items, key=lambda i: (i.relation.relation_id,
                                                      i.unit_name)),
                         key='unit_name')

    @property
    def received(self):
        """
        Combined `UnitDataView` of the data of all units in this list,
        as raw strings.
        """
        return self.received_json.data

    @property
    def received_json(self):
        """
        Combined `JSONUnitDataView` of the data of all units in this list,
        with automatic JSON decoding.
        """
        if not hasattr(self, '_data'):
            # NB: units are reversed so that lowest numbered unit takes precedence
            self._data = JSONUnitDataView({key: value
                                           for unit in reversed(self)
                                           for key, value in unit.received.items()})

        return self._data


class UnitDataView(UserDict):
    """
    View of a dict containing a unit's data.

    This is like a ``defaultdict(lambda: None)`` which cannot be
    modified by default.
    """
    def __init__(self, data, writeable=False):
        self.data = data
        self._writeable = writeable
        self._modified = False

    @property
    def modified(self):
        """
        Whether this collection has been modified.
        """
        return self._modified

    @property
    def writeable(self):
        """
        Whether this collection can be modified.
        """
        return self._writeable

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __getitem__(self, key):
        return self.data.get(key)

    def __setitem__(self, key, value):
        if not self._writeable:
            raise ValueError('Remote unit data cannot be modified')
        self._modified = True
        self.data[key] = value


class JSONUnitDataView(UserDict):
    """
    View of a dict that performs automatic JSON en/decoding of items.

    Like `UnitDataView`, this is like a ``defaultdict(lambda: None)`` which
    cannot be modified by default.

    When decoding, if a value fails to decode, it will just return the raw
    value as a string.

    When encoding, it ensures that keys are sorted to maintain stable and
    consistent encoded representations.

    A `UnitDataView` of the original dict, without automatic en/decoding,
    can be accessed as ``self.data``.
    """
    def __init__(self, data, writeable=False):
        self.data = UnitDataView(data, writeable)

    @property
    def modified(self):
        """
        Whether this collection has been modified.
        """
        return self.data.modified

    @property
    def writeable(self):
        """
        Whether this collection can be modified.
        """
        return self.data.writeable

    def get(self, key, default=None):
        if key not in self.data:
            return default
        return self[key]

    def __getitem__(self, key):
        value = self.data[key]
        if not value:
            return value
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def __setitem__(self, key, value):
        self.data[key] = json.dumps(value, sort_keys=True)


hookenv.atstart(Endpoint._startup)
