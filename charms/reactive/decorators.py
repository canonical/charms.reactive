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

from six.moves import filter, map
from functools import wraps, partial

from charmhelpers.core import hookenv
from charms.reactive.bus import Handler
from charms.reactive.bus import get_states
from charms.reactive.bus import _action_id
from charms.reactive.bus import _short_action_id
from charms.reactive.relations import RelationBase
from charms.reactive.helpers import _hook
from charms.reactive.helpers import _when_all
from charms.reactive.helpers import _when_any
from charms.reactive.helpers import _when_none
from charms.reactive.helpers import _when_not_all
from charms.reactive.helpers import any_file_changed
from charms.reactive.helpers import was_invoked
from charms.reactive.helpers import mark_invoked


def hook(*hook_patterns):
    """
    Register the decorated function to run when the current hook matches any of
    the ``hook_patterns``.

    The hook patterns can use the ``{interface:...}`` and ``{A,B,...}`` syntax
    supported by :func:`~charms.reactive.bus.any_hook`.

    If the hook is a relation hook, an instance of that relation class will be
    passed in to the decorated function.

    For example, to match any joined or changed hook for the relation providing
    the ``mysql`` interface::

        class MySQLRelation(RelationBase):
            @hook('{provides:mysql}-relation-{joined,changed}')
            def joined_or_changed(self):
                pass

    Note that hook decorators **cannot** be combined with :func:`when` or
    :func:`when_not` decorators.
    """
    def _register(action):
        def arg_gen():
            # use a generator to defer calling of hookenv.relation_type, for tests
            rel = RelationBase.from_name(hookenv.relation_type())
            if rel:
                yield rel

        handler = Handler.get(action)
        handler.add_predicate(partial(_hook, hook_patterns))
        handler.add_args(arg_gen())
        return action
    return _register


def when(*desired_states):
    """
    Alias for `when_all`.
    """
    return when_all(*desired_states)


def when_all(*desired_states):
    """
    Register the decorated function to run when all of ``desired_states`` are active.

    This decorator will pass zero or more relation instances to the handler, if
    any of the states are associated with relations.  If so, they will be passed
    in in the same order that the states are given to the decorator.

    Note that handlers whose conditions match are triggered at least once per
    hook invocation.
    """
    def _register(action):
        handler = Handler.get(action)
        handler.add_predicate(partial(_when_all, desired_states))
        handler.add_args(filter(None, map(RelationBase.from_state, desired_states)))
        handler.register_states(desired_states)
        return action
    return _register


def when_any(*desired_states):
    """
    Register the decorated function to run when any of ``desired_states`` are active.

    This decorator will never cause arguments to be passed into to the handler,
    even for states which are set by relations, since that would make the
    parameter bindings ambiguous.  Therefore, it is not generally recommended
    to use this with relation states; however, if you do need to, you can get
    the relation instance associated with a state using
    :func:`~charms.reactive.relations.RelationBase.from_state`.

    Note that handlers whose conditions match are triggered at least once per
    hook invocation.
    """
    def _register(action):
        handler = Handler.get(action)
        handler.add_predicate(partial(_when_any, desired_states))
        handler.register_states(desired_states)
        return action
    return _register


def when_not(*desired_states):
    """
    Alias for `when_none`.
    """
    return when_none(*desired_states)


def when_none(*desired_states):
    """
    Register the decorated function to run when none of ``desired_states`` are
    active.

    This decorator will never cause arguments to be passed to the handler.

    Note that handlers whose conditions match are triggered at least once per
    hook invocation.
    """
    def _register(action):
        handler = Handler.get(action)
        handler.add_predicate(partial(_when_none, desired_states))
        handler.register_states(desired_states)
        return action
    return _register


def when_not_all(*desired_states):
    """
    Register the decorated function to run when one or more of the
    ``desired_states`` are not active.

    This decorator will never cause arguments to be passed to the handler.

    Note that handlers whose conditions match are triggered at least once per
    hook invocation.
    """
    def _register(action):
        handler = Handler.get(action)
        handler.add_predicate(partial(_when_not_all, desired_states))
        handler.register_states(desired_states)
        return action
    return _register


def when_file_changed(*filenames, **kwargs):
    """
    Register the decorated function to run when one or more files have changed.

    :param list filenames: The names of one or more files to check for changes
        (a callable returning the name is also accepted).
    :param str hash_type: The type of hash to use for determining if a file has
        changed.  Defaults to 'md5'.  Must be given as a kwarg.
    """
    def _register(action):
        handler = Handler.get(action)
        handler.add_predicate(partial(any_file_changed, filenames, **kwargs))
        return action
    return _register


def not_unless(*desired_states):
    """
    Assert that the decorated function can only be called if the desired_states
    are active.

    Note that, unlike :func:`when`, this does **not** trigger the decorated
    function if the states match.  It **only** raises an exception if the
    function is called when the states do not match.

    This is primarily for informational purposes and as a guard clause.
    """
    def _decorator(func):
        action_id = _action_id(func)
        short_action_id = _short_action_id(func)

        @wraps(func)
        def _wrapped(*args, **kwargs):
            active_states = get_states()
            missing_states = [state for state in desired_states if state not in active_states]
            if missing_states:
                hookenv.log('%s called before state%s: %s' % (
                    short_action_id,
                    's' if len(missing_states) > 1 else '',
                    ', '.join(missing_states)), hookenv.WARNING)
            return func(*args, **kwargs)
        _wrapped._action_id = action_id
        _wrapped._short_action_id = short_action_id
        return _wrapped
    return _decorator


def only_once(action=None):
    """
    Register the decorated function to be run once, and only once.

    This decorator will never cause arguments to be passed to the handler.
    """
    if action is None:
        # allow to be used as @only_once or @only_once()
        return only_once

    action_id = _action_id(action)
    handler = Handler.get(action)
    handler.add_predicate(lambda: not was_invoked(action_id))
    handler.add_post_callback(partial(mark_invoked, action_id))
    return action
