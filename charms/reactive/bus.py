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
import re
import sys
import errno
import subprocess
from itertools import chain
from functools import partial

from six.moves import range

from charmhelpers.core import hookenv
from charmhelpers.core import unitdata
from charmhelpers.cli import cmdline

try:
    # Python 3
    from importlib.machinery import SourceFileLoader

    def load_source(modname, realpath):
        return SourceFileLoader(modname, realpath).load_module()
except ImportError:
    # Python 2
    from imp import load_source


_log_opts = os.environ.get('REACTIVE_LOG_OPTS', '').split(',')
LOG_OPTS = {
    'register': 'register' in _log_opts,
}


class BrokenHandlerException(Exception):
    def __init__(self, path):
        message = ("File at '{}' is marked as executable but "
                   "execution failed. Only handler files may be marked "
                   "as executable.".format(path))
        super(BrokenHandlerException, self).__init__(message)


class State(str):
    """
    A reactive state that can be set.

    States are essentially just strings, but this class should be used to enable them
    to be discovered and introspected, for documentation, composition, or linting.

    This should be used with :class:`StateList`.
    """
    pass


class StateList(object):
    """
    Base class for a set of states that can be set by a relation or layer.

    This class should be used so that they can be discovered and introspected,
    for documentation, composition, or linting.

    Example usage::

        class MyRelation(RelationBase):
            class states(StateList):
                connected = State('{relation_name}.connected')
                available = State('{relation_name}.available')
    """
    pass


@cmdline.subcommand()
@cmdline.no_output
def set_state(state, value=None):
    """
    Set the given state as active, optionally associating with a relation.
    """
    old_states = get_states()
    unitdata.kv().update({state: value}, prefix='reactive.states.')
    if state not in old_states:
        StateWatch.change(state)


@cmdline.subcommand()
@cmdline.no_output
def remove_state(state):
    """
    Remove / deactivate a state.
    """
    old_states = get_states()
    unitdata.kv().unset('reactive.states.%s' % state)
    unitdata.kv().set('reactive.dispatch.removed_state', True)
    if state in old_states:
        StateWatch.change(state)


@cmdline.subcommand()
def get_states():
    """
    Return a mapping of all active states to their values.
    """
    return unitdata.kv().getrange('reactive.states.', strip=True) or {}


class StateWatch(object):
    key = 'reactive.state_watch'

    @classmethod
    def _store(cls):
        return unitdata.kv()

    @classmethod
    def _get(cls):
        return cls._store().get(cls.key, {
            'iteration': 0,
            'changes': [],
            'pending': [],
        })

    @classmethod
    def _set(cls, data):
        cls._store().set(cls.key, data)

    @classmethod
    def reset(cls):
        cls._store().unset(cls.key)

    @classmethod
    def iteration(cls, i):
        data = cls._get()
        data['iteration'] = i
        cls._set(data)

    @classmethod
    def watch(cls, watcher, states):
        data = cls._get()
        iteration = data['iteration']
        changed = bool(set(states) & set(data['changes']))
        return iteration == 0 or changed

    @classmethod
    def change(cls, state):
        data = cls._get()
        data['pending'].append(state)
        cls._set(data)

    @classmethod
    def commit(cls):
        data = cls._get()
        data['changes'] = data['pending']
        data['pending'] = []
        cls._set(data)


def get_state(state, default=None):
    """Return the value associated with an active state, or None"""
    return unitdata.kv().get('reactive.states.%s' % state, default)


def _action_id(action):
    if hasattr(action, '_action_id'):
        return action._action_id
    return "%s:%s:%s" % (action.__code__.co_filename,
                         action.__code__.co_firstlineno,
                         action.__code__.co_name)


def _short_action_id(action):
    if hasattr(action, '_short_action_id'):
        return action._short_action_id
    filepath = os.path.relpath(action.__code__.co_filename, hookenv.charm_dir())
    return "%s:%s:%s" % (filepath,
                         action.__code__.co_firstlineno,
                         action.__code__.co_name)


class Handler(object):
    """
    Class representing a reactive state handler.
    """
    _HANDLERS = {}
    _CONSUMED_STATES = set()

    @classmethod
    def get(cls, action):
        """
        Get or register a handler for the given action.

        :param func action: Callback that is called when invoking the Handler
        :param func args_source: Optional callback that generates args for the action
        """
        action_id = _action_id(action)
        if action_id not in cls._HANDLERS:
            if LOG_OPTS['register']:
                hookenv.log('Registering reactive handler for %s' % _short_action_id(action), level=hookenv.DEBUG)
            cls._HANDLERS[action_id] = cls(action)
        return cls._HANDLERS[action_id]

    @classmethod
    def get_handlers(cls):
        """
        Clear all registered handlers.
        """
        return cls._HANDLERS.values()

    @classmethod
    def clear(cls):
        """
        Clear all registered handlers.
        """
        cls._HANDLERS = {}

    def __init__(self, action):
        """
        Create a new Handler.

        :param func action: Callback that is called when invoking the Handler
        :param func args_source: Optional callback that generates args for the action
        """
        self._action_id = _short_action_id(action)
        self._action = action
        self._args = []
        self._predicates = []
        self._post_callbacks = []
        self._states = set()

    def id(self):
        return self._action_id

    def add_args(self, args):
        """
        Add arguments to be passed to the action when invoked.

        :param args: Any sequence or iterable, which will be lazily evaluated
            to provide args.  Subsequent calls to :meth:`add_args` can be used
            to add additional arguments.
        """
        self._args.append(args)

    def add_predicate(self, predicate):
        """
        Add a new predicate callback to this handler.
        """
        _predicate = predicate
        if isinstance(predicate, partial):
            _predicate = 'partial(%s, %s, %s)' % (predicate.func, predicate.args, predicate.keywords)
        if LOG_OPTS['register']:
            hookenv.log('  Adding predicate for %s: %s' % (self.id(), _predicate), level=hookenv.DEBUG)
        self._predicates.append(predicate)

    def add_post_callback(self, callback):
        """
        Add a callback to be run after the action is invoked.
        """
        self._post_callbacks.append(callback)

    def test(self):
        """
        Check the predicate(s) and return True if this handler should be invoked.
        """
        if self._states and not StateWatch.watch(self._action_id, self._states):
            return False
        return all(predicate() for predicate in self._predicates)

    def _get_args(self):
        """
        Lazily evaluate the args.
        """
        if not hasattr(self, '_args_evaled'):
            # cache the args in case handler is re-invoked due to states change
            self._args_evaled = list(chain.from_iterable(self._args))
        return self._args_evaled

    def invoke(self):
        """
        Invoke this handler.
        """
        args = self._get_args()
        self._action(*args)
        for callback in self._post_callbacks:
            callback()

    def register_states(self, states):
        """
        Register states as being relevant to this handler.

        Relevant states will be used to determine if the handler should
        be re-invoked due to changes in the set of active states.  If this
        handler has already been invoked during this :func:`dispatch` run
        and none of its relevant states have been set or removed since then,
        then the handler will be skipped.

        This is also used for linting and composition purposes, to determine
        if a layer has unhandled states.
        """
        self._CONSUMED_STATES.update(states)
        self._states.update(states)


class ExternalHandler(Handler):
    """
    A variant Handler for external executable actions (such as bash scripts).

    External handlers must adhere to the following protocol:

      * The handler can be any executable

      * When invoked with the ``--test`` command-line flag, it should exit with
        an exit code of zero to indicate that the handler should be invoked, and
        a non-zero exit code to indicate that it need not be invoked.  It can
        also provide a line of output to be passed to the ``--invoke`` call, e.g.,
        to indicate which sub-handlers should be invoked.  The handler should
        **not** perform its action when given this flag.

      * When invoked with the ``--invoke`` command-line flag (which will be
        followed by any output returned by the ``--test`` call), the handler
        should perform its action(s).
    """
    @classmethod
    def register(cls, filepath):
        if filepath not in Handler._HANDLERS:
            _filepath = os.path.relpath(filepath, hookenv.charm_dir())
            if LOG_OPTS['register']:
                hookenv.log('Registering external reactive handler for %s' % _filepath, level=hookenv.DEBUG)
            Handler._HANDLERS[filepath] = cls(filepath)
        return Handler._HANDLERS[filepath]

    def __init__(self, filepath):
        self._filepath = filepath
        self._test_output = ''

    def id(self):
        _filepath = os.path.relpath(self._filepath, hookenv.charm_dir())
        return '%s "%s"' % (_filepath, self._test_output)

    def test(self):
        """
        Call the external handler to test whether it should be invoked.
        """
        # flush to ensure external process can see states as they currently
        # are, and write states (flush releases lock)
        unitdata.kv().flush()
        try:
            proc = subprocess.Popen([self._filepath, '--test'], stdout=subprocess.PIPE, env=os.environ)
        except OSError as oserr:
            if oserr.errno == errno.ENOEXEC:
                raise BrokenHandlerException(self._filepath)
            raise
        self._test_output, _ = proc.communicate()
        return proc.returncode == 0

    def invoke(self):
        """
        Call the external handler to be invoked.
        """
        # flush to ensure external process can see states as they currently
        # are, and write states (flush releases lock)
        unitdata.kv().flush()
        subprocess.check_call([self._filepath, '--invoke', self._test_output], env=os.environ)


def dispatch():
    """
    Dispatch registered handlers.

    Handlers are dispatched according to the following rules:

    * Handlers are repeatedly tested and invoked in iterations, until the system
      settles into quiescence (that is, until no new handlers match to be invoked).

    * In the first iteration, :func:`@hook <charms.reactive.decorators.hook>`
      and :func:`@action <charms.reactive.decorators.action>` handlers will
      be invoked, if they match.

    * In subsequent iterations, other handlers are invoked, if they match.

    * Added states will not trigger new handlers until the next iteration,
      to ensure that chained states are invoked in a predictable order.

    * Removed states will cause the current set of matched handlers to be
      re-tested, to ensure that no handler is invoked after its matching
      state has been removed.

    * Other than the guarantees mentioned above, the order in which matching
      handlers are invoked is undefined.

    * States are preserved between hook and action invocations, and all matching
      handlers are re-invoked for every hook and action.  There are
      :doc:`decorators <charms.reactive.decorators>` and
      :doc:`helpers <charms.reactive.helpers>`
      to prevent unnecessary reinvocations, such as
      :func:`~charms.reactive.decorators.only_once`.
    """
    StateWatch.reset()

    def _test(to_test):
        return list(filter(lambda h: h.test(), to_test))

    def _invoke(to_invoke):
        while to_invoke:
            unitdata.kv().set('reactive.dispatch.removed_state', False)
            for handler in list(to_invoke):
                to_invoke.remove(handler)
                hookenv.log('Invoking reactive handler: %s' % handler.id(), level=hookenv.INFO)
                handler.invoke()
                if unitdata.kv().get('reactive.dispatch.removed_state'):
                    # re-test remaining handlers
                    to_invoke = _test(to_invoke)
                    break
        StateWatch.commit()

    unitdata.kv().set('reactive.dispatch.phase', 'hooks')
    hook_handlers = _test(Handler.get_handlers())
    _invoke(hook_handlers)

    unitdata.kv().set('reactive.dispatch.phase', 'other')
    for i in range(100):
        StateWatch.iteration(i)
        other_handlers = _test(Handler.get_handlers())
        if not other_handlers:
            break
        _invoke(other_handlers)

    StateWatch.reset()


def discover():
    """
    Discover handlers based on convention.

    Handlers will be loaded from the following directories and their subdirectories:

      * ``$CHARM_DIR/reactive/``
      * ``$CHARM_DIR/hooks/reactive/``
      * ``$CHARM_DIR/hooks/relations/``

    They can be Python files, in which case they will be imported and decorated
    functions registered.  Or they can be executables, in which case they must
    adhere to the :class:`ExternalHandler` protocol.
    """
    for search_dir in ('reactive', 'hooks/reactive', 'hooks/relations'):
        search_path = os.path.join(hookenv.charm_dir(), search_dir)
        for dirpath, dirnames, filenames in os.walk(search_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                _register_handlers_from_file(filepath)


def _load_module(filepath):
    realpath = os.path.realpath(filepath)
    for module in sys.modules.values():
        if not hasattr(module, '__file__'):
            continue  # ignore builtins
        modpath = os.path.realpath(re.sub(r'\.pyc$', '.py', module.__file__))
        if realpath == modpath:
            return module
    else:
        modname = realpath.replace('.', '_').replace(os.sep, '_')
        sys.modules[modname] = load_source(modname, realpath)
        return sys.modules[modname]


def _register_handlers_from_file(filepath):
    no_exec_blacklist = (
        '.md', '.yaml', '.txt', '.ini',
        'makefile', '.gitignore',
        'copyright', 'license')
    if filepath.lower().endswith(no_exec_blacklist):
        # Don't load handlers with one of the blacklisted extensions
        return
    if filepath.endswith('.py'):
        _load_module(filepath)
    elif os.access(filepath, os.X_OK):
        ExternalHandler.register(filepath)
