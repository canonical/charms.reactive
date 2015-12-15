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

import os
from inspect import isclass

from six import with_metaclass

from charmhelpers.core import hookenv
from charmhelpers.core import unitdata
from charmhelpers.cli import cmdline
from charms.reactive.bus import get_state
from charms.reactive.bus import set_state
from charms.reactive.bus import remove_state
from charms.reactive.bus import _load_module
from charms.reactive.bus import StateList


ALL = '__ALL_SERVICES__'


class scopes(object):
    """
    These are the recommended scope values for relation implementations.

    To use, simply set the ``scope`` class variable to one of these::

        class MyRelationClient(RelationBase):
            scope = scopes.SERVICE
    """

    GLOBAL = 'global'
    """
    All connected services and units for this relation will share a single
    conversation.  The same data will be broadcast to every remote unit, and
    retrieved data will be aggregated across all remote units and is expected
    to either eventually agree or be set by a single leader.
    """

    SERVICE = 'service'
    """
    Each connected service for this relation will have its own conversation.
    The same data will be broadcast to every unit of each service's conversation,
    and data from all units of each service will be aggregated and is expected
    to either eventually agree or be set by a single leader.
    """

    UNIT = 'unit'
    """
    Each connected unit for this relation will have its own conversation.  This
    is the default scope.  Each unit's data will be retrieved individually, but
    note that due to how Juju works, the same data is still broadcast to all
    units of a single service.
    """


class AutoAccessors(type):
    """
    Metaclass that converts fields referenced by ``auto_accessors`` into
    accessor methods with very basic doc strings.
    """
    def __new__(cls, name, parents, dct):
        for field in dct.get('auto_accessors', []):
            meth_name = field.replace('-', '_')
            meth = cls._accessor(field)
            meth.__name__ = meth_name
            meth.__module__ = dct.get('__module__')
            meth.__doc__ = 'Get the %s, if available, or None.' % field
            dct[meth_name] = meth
        return super(AutoAccessors, cls).__new__(cls, name, parents, dct)

    @staticmethod
    def _accessor(field):
        def __accessor(self):
            return self.get_remote(field)
        return __accessor


class RelationBase(with_metaclass(AutoAccessors, object)):
    """
    The base class for all relation implementations.
    """
    _cache = {}

    scope = scopes.UNIT
    """
    Conversation scope for this relation.

    The conversation scope controls how communication with connected units
    is aggregated into related :class:`Conversations <Conversation>`, and
    can be any of the predefined :class:`scopes`, or any arbitrary string.
    Connected units which share the same scope will be considered part of
    the same conversation.  Data sent to a conversation is sent to all units
    that are a part of that conversation, and units that are part of a
    conversation are expected to agree on the data that they send, whether
    via eventual consistency or by having a single leader set the data.

    The default scope is :attr:`scopes.UNIT`.
    """

    class states(StateList):
        """
        This is the set of :class:`States <charms.reactive.bus.State>` that this
        relation could set.

        This should be defined by the relation subclass to ensure that
        states are consistent and documented, as well as being discoverable
        and introspectable by linting and composition tools.

        For example::

            class MyRelationClient(RelationBase):
                scope = scopes.GLOBAL
                auto_accessors = ['host', 'port']

                class states(StateList):
                    connected = State('{relation_name}.connected')
                    available = State('{relation_name}.available')

                @hook('{requires:my-interface}-relation-{joined,changed}')
                def changed(self):
                    self.set_state(self.states.connected)
                    if self.host() and self.port():
                        self.set_state(self.states.available)
        """
        pass

    auto_accessors = []
    """
    Remote field names to be automatically converted into accessors with
    basic documentation.

    These accessors will just call :meth:`get_remote` using the
    :meth:`default conversation <conversation>`.  Note that it is highly
    recommended that this be used only with :attr:`scopes.GLOBAL` scope.
    """

    def __init__(self, relation_name, conversations=None):
        self._relation_name = relation_name
        self._conversations = conversations or [Conversation.join(self.scope)]

    @property
    def relation_name(self):
        """
        Name of the relation this instance is handling.
        """
        return self._relation_name

    @classmethod
    def from_state(cls, state):
        """
        Find relation implementation in the current charm, based on the
        name of an active state.
        """
        value = get_state(state)
        if value is None:
            return None
        relation_name = value['relation']
        conversations = Conversation.load(value['conversations'])
        return cls.from_name(relation_name, conversations)

    @classmethod
    def from_name(cls, relation_name, conversations=None):
        """
        Find relation implementation in the current charm, based on the
        ID of the relation.

        :return: A Relation instance, or None
        """
        if relation_name is None:
            return None
        relation_class = cls._cache.get(relation_name)
        if relation_class:
            return relation_class(relation_name, conversations)
        role, interface = hookenv.relation_to_role_and_interface(relation_name)
        if role and interface:
            relation_class = cls._find_impl(role, interface)
            if relation_class:
                cls._cache[relation_name] = relation_class
                return relation_class(relation_name, conversations)
        return None

    @classmethod
    def _find_impl(cls, role, interface):
        """
        Find relation implementation based on its role and interface.

        Looks for the first file matching:
        ``$CHARM_DIR/hooks/relations/{interface}/{provides,requires,peer}.py``
        """
        hooks_dir = os.path.join(hookenv.charm_dir(), 'hooks')
        try:
            filepath = os.path.join(hooks_dir, 'relations', interface, role + '.py')
            module = _load_module(filepath)
            return cls._find_subclass(module)
        except ImportError:
            return None

    @classmethod
    def _find_subclass(cls, module):
        """
        Attempt to find subclass of :class:`RelationBase` in the given module.

        Note: This means strictly subclasses and not :class:`RelationBase` itself.
        This is to prevent picking up :class:`RelationBase` being imported to be
        used as the base class.
        """
        for attr in dir(module):
            candidate = getattr(module, attr)
            if isclass(candidate) and issubclass(candidate, cls) and candidate is not cls:
                return candidate
        return None

    def conversations(self):
        """
        Return a list of the conversations that this relation is currently handling.

        Note that "currently handling" means for the current state or hook context,
        and not all conversations that might be active for this relation for other
        states.
        """
        return list(self._conversations)

    def conversation(self, scope=None):
        """
        Get a single conversation, by scope, that this relation is currently handling.

        If the scope is not given, the correct scope is inferred by the current
        hook execution context.  If there is no current hook execution context, it
        is assume that there is only a single global conversation scope for this
        relation.  If this relation's scope is not global and there is no current
        hook execution context, then an error is raised.
        """
        if scope is None:
            if self.scope is scopes.UNIT:
                scope = hookenv.remote_unit()
            elif self.scope is scopes.SERVICE:
                scope = hookenv.remote_service_name()
            else:
                scope = self.scope
        if scope is None:
            raise ValueError('Unable to determine default scope: no current hook or global scope')
        for conversation in self._conversations:
            if conversation.scope == scope:
                return conversation
        else:
            raise ValueError("Conversation with scope '%s' not found" % scope)

    def set_state(self, state, scope=None):
        """
        Set the state for the :class:`Conversation` with the given scope.

        In Python, this is equivalent to::

            relation.conversation(scope).set_state(state)

        See :meth:`conversation` and :meth:`Conversation.set_state`.
        """
        self.conversation(scope).set_state(state)

    def remove_state(self, state, scope=None):
        """
        Remove the state for the :class:`Conversation` with the given scope.

        In Python, this is equivalent to::

            relation.conversation(scope).remove_state(state)

        See :meth:`conversation` and :meth:`Conversation.remove_state`.
        """
        self.conversation(scope).remove_state(state)

    def is_state(self, state, scope=None):
        """
        Test the state for the :class:`Conversation` with the given scope.

        In Python, this is equivalent to::

            relation.conversation(scope).is_state(state)

        See :meth:`conversation` and :meth:`Conversation.is_state`.
        """
        return self.conversation(scope).is_state(state)

    def toggle_state(self, state, active=None, scope=None):
        """
        Toggle the state for the :class:`Conversation` with the given scope.

        In Python, this is equivalent to::

            relation.conversation(scope).toggle_state(state)

        See :meth:`conversation` and :meth:`Conversation.toggle_state`.
        """
        self.conversation(scope).toggle_state(state, active)

    def set_remote(self, key=None, value=None, data=None, scope=None, **kwdata):
        """
        Set data for the remote end(s) of the :class:`Conversation` with the given scope.

        In Python, this is equivalent to::

            relation.conversation(scope).set_remote(key, value, data, scope, **kwdata)

        See :meth:`conversation` and :meth:`Conversation.set_remote`.
        """
        self.conversation(scope).set_remote(key, value, data, **kwdata)

    def get_remote(self, key, default=None, scope=None):
        """
        Get data from the remote end(s) of the :class:`Conversation` with the given scope.

        In Python, this is equivalent to::

            relation.conversation(scope).get_remote(key, default)

        See :meth:`conversation` and :meth:`Conversation.get_remote`.
        """
        return self.conversation(scope).get_remote(key, default)

    def set_local(self, key=None, value=None, data=None, scope=None, **kwdata):
        """
        Locally store some data, namespaced by the current or given :class:`Conversation` scope.

        In Python, this is equivalent to::

            relation.conversation(scope).set_local(data, scope, **kwdata)

        See :meth:`conversation` and :meth:`Conversation.set_local`.
        """
        self.conversation(scope).set_local(key, value, data, **kwdata)

    def get_local(self, key, default=None, scope=None):
        """
        Retrieve some data previously set via :meth:`set_local`.

        In Python, this is equivalent to::

            relation.conversation(scope).get_local(key, default)

        See :meth:`conversation` and :meth:`Conversation.get_local`.
        """
        return self.conversation(scope).get_local(key, default)


class Conversation(object):
    """
    Converations are the persistent, evolving, two-way communication between
    this service and one or more remote services.

    Conversations are not limited to a single Juju hook context.  They represent
    the entire set of interactions between the end-points from the time the
    relation is joined until it is departed.

    Conversations evolve over time, moving from one semantic state to the next
    as the communication progresses.

    Conversations may encompass multiple remote services or units.  While a
    database client would connect to only a single database, that database will
    likely serve several other services.  On the other hand, while the database
    is only concerned about providing a database to each service as a whole, a
    load-balancing proxy must consider each unit of each service individually.

    Conversations use the idea of :class:`scope` to determine how units and
    services are grouped together.
    """
    def __init__(self, relation_name=None, units=None, scope=None):
        self.relation_name = relation_name or hookenv.relation_type()
        self.units = set(units or [hookenv.remote_unit()])
        self.scope = scope or hookenv.remote_unit()

    @property
    def key(self):
        """
        The key under which this conversation will be stored.
        """
        return 'reactive.conversations.%s.%s' % (self.relation_name, self.scope)

    @property
    @hookenv.cached
    def relation_ids(self):
        """
        The set of IDs of the specific relation instances that this conversation
        is communicating with.
        """
        relation_ids = []
        services = set(unit.split('/')[0] for unit in self.units)
        for relation_id in hookenv.relation_ids(self.relation_name):
            if hookenv.remote_service_name(relation_id) in services:
                relation_ids.append(relation_id)
        return relation_ids

    @classmethod
    def join(cls, scope):
        """
        Get or create a conversation for the given scope and active hook context.

        The current remote unit for the active hook context will be added to
        the conversation.

        Note: This uses :mod:`charmhelpers.core.unitdata` and requires that
        :meth:`~charmhelpers.core.unitdata.Storage.flush` be called.
        """
        relation_name = hookenv.relation_type()
        unit = hookenv.remote_unit()
        service = hookenv.remote_service_name()
        if scope is scopes.UNIT:
            scope = unit
        elif scope is scopes.SERVICE:
            scope = service
        key = 'reactive.conversations.%s.%s' % (relation_name, scope)
        conversation = cls.deserialize(unitdata.kv().get(key, {'scope': scope}))
        conversation.units.add(unit)
        unitdata.kv().set(key, cls.serialize(conversation))
        return conversation

    def depart(self):
        """
        Remove the current remote unit, for the active hook context, from
        this conversation.  This should be called from a `-departed` hook.

        TODO: Need to figure out a way to have this called implicitly, to
        ensure cleaning up of conversations that are no longer needed.
        """
        unit = hookenv.remote_unit()
        self.units.remove(unit)
        if self.units:
            unitdata.kv().set(self.key, self.serialize(self))
        else:
            unitdata.kv().unset(self.key)

    @classmethod
    def deserialize(cls, conversation):
        """
        Deserialize a :meth:`serialized <serialize>` conversation.
        """
        return cls(**conversation)

    @classmethod
    def serialize(cls, conversation):
        """
        Serialize a conversation instance for storage.
        """
        return {
            'relation_name': conversation.relation_name,
            'units': list(conversation.units),
            'scope': conversation.scope,
        }

    @classmethod
    def load(cls, keys):
        """
        Load a set of conversations by their keys.
        """
        conversations = []
        for key in keys:
            conversation = unitdata.kv().get(key)
            if conversation:
                conversations.append(cls.deserialize(conversation))
        return conversations

    def set_state(self, state):
        """
        Activate and put this conversation into the given state.

        The relation name will be interpolated in the state name, and it is
        recommended that it be included to avoid conflicts with states from
        other relations.  For example::

            conversation.set_state('{relation_name}.state')

        If called from a converation handling the relation "foo", this will
        activate the "foo.state" state, and will add this conversation to
        that state.

        Note: This uses :mod:`charmhelpers.core.unitdata` and requires that
        :meth:`~charmhelpers.core.unitdata.Storage.flush` be called.
        """
        state = state.format(relation_name=self.relation_name)
        value = get_state(state, {
            'relation': self.relation_name,
            'conversations': [],
        })
        if self.key not in value['conversations']:
            value['conversations'].append(self.key)
        set_state(state, value)

    def remove_state(self, state):
        """
        Remove this conversation from the given state, and potentially
        deactivate the state if no more conversations are in it.

        The relation name will be interpolated in the state name, and it is
        recommended that it be included to avoid conflicts with states from
        other relations.  For example::

            conversation.remove_state('{relation_name}.state')

        If called from a converation handling the relation "foo", this will
        remove the conversation from the "foo.state" state, and, if no more
        conversations are in this the state, will deactivate it.
        """
        state = state.format(relation_name=self.relation_name)
        value = get_state(state)
        if not value:
            return
        if self.key in value['conversations']:
            value['conversations'].remove(self.key)
        if value['conversations']:
            set_state(state, value)
        else:
            remove_state(state)

    def is_state(self, state):
        """
        Test if this conversation is in the given state.
        """
        state = state.format(relation_name=self.relation_name)
        value = get_state(state)
        if not value:
            return False
        return self.key in value['conversations']

    def toggle_state(self, state, active=None):
        """
        Toggle the given state for this conversation.

        The state will be set ``active`` is ``True``, otherwise the state will be removed.

        If ``active`` is not given, it will default to the inverse of the current state
        (i.e., ``False`` if the state is currently set, ``True`` if it is not; essentially
        toggling the state).

        For example::

            conv.toggle_state('{relation_name}.foo', value=='foo')

        This will set the state if ``value`` is equal to ``foo``.
        """
        if active is None:
            active = not self.is_state(state)
        if active:
            self.set_state(state)
        else:
            self.remove_state(state)

    def set_remote(self, key=None, value=None, data=None, **kwdata):
        """
        Set data for the remote end(s) of this conversation.

        Data can be passed in either as a single dict, or as key-word args.

        Note that, in Juju, setting relation data is inherently service scoped.
        That is, if the conversation only includes a single unit, the data will
        still be set for that unit's entire service.

        However, if this conversation's scope encompasses multiple services,
        the data will be set for all of those services.

        :param str key: The name of a field to set.
        :param value: A value to set.
        :param dict data: A mapping of keys to values.
        :param \*\*kwdata: A mapping of keys to values, as keyword arguments.
        """
        if data is None:
            data = {}
        if key is not None:
            data[key] = value
        data.update(kwdata)
        if not data:
            return
        for relation_id in self.relation_ids:
            hookenv.relation_set(relation_id, data)

    def get_remote(self, key, default=None):
        """
        Get a value from the remote end(s) of this conversation.

        Note that if a conversation's scope encompasses multiple units, then
        those units are expected to agree on their data, whether that is through
        relying on a single leader to set the data or by all units eventually
        converging to identical data.  Thus, this method returns the first
        value that it finds set by any of its units.
        """
        for relation_id in self.relation_ids:
            for unit in hookenv.related_units(relation_id):
                if unit not in self.units:
                    continue
                value = hookenv.relation_get(key, unit, relation_id)
                if value:
                    return value
        return default

    def set_local(self, key=None, value=None, data=None, **kwdata):
        """
        Locally store some data associated with this conversation.

        Data can be passed in either as a single dict, or as key-word args.

        For example, if you need to store the previous value of a remote field
        to determine if it has changed, you can use the following::

            prev = conversation.get_local('field')
            curr = conversation.get_remote('field')
            if prev != curr:
                handle_change(prev, curr)
                conversation.set_local('field', curr)

        Note: This uses :mod:`charmhelpers.core.unitdata` and requires that
        :meth:`~charmhelpers.core.unitdata.Storage.flush` be called.

        :param str key: The name of a field to set.
        :param value: A value to set.
        :param dict data: A mapping of keys to values.
        :param \*\*kwdata: A mapping of keys to values, as keyword arguments.
        """
        if data is None:
            data = {}
        if key is not None:
            data[key] = value
        data.update(kwdata)
        if not data:
            return
        unitdata.kv().update(data, prefix='%s.%s.' % (self.key, 'local-data'))

    def get_local(self, key, default=None):
        """
        Retrieve some data previously set via :meth:`set_local` for this conversation.
        """
        key = '%s.%s.%s' % (self.key, 'local-data', key)
        return unitdata.kv().get(key, default)


@cmdline.subcommand()
def relation_call(method, relation_name=None, state=None, *args):
    """Invoke a method on the class implementing a relation via the CLI"""
    if relation_name:
        relation = RelationBase.from_name(relation_name)
        if relation is None:
            raise ValueError('Relation not found: %s' % relation_name)
    elif state:
        relation = RelationBase.from_state(state)
        if relation is None:
            raise ValueError('Relation not found: %s' % state)
    else:
        raise ValueError('Must specify either relation_name or state')
    result = getattr(relation, method)(*args)
    if method == 'conversations':
        # special case for conversations to make them work from CLI
        result = [c.scope for c in result]
    return result
