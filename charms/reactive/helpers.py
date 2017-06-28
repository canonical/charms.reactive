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

import re
import json
import hashlib

from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core import unitdata
from charmhelpers.cli import cmdline
from charms.reactive import deprecated
from charms.reactive.bus import set_flag, clear_flag, get_flags


@deprecated.alias('toggle_state')
def toggle_flag(flag, should_set):
    """
    Helper that calls either :func:`set_flag` or :func:`clear_flag`,
    depending on the value of `should_set`.

    Equivalent to::

        if should_set:
            set_flag(flag)
        else:
            clear_flag(flag)

    :param str flag: Name of flag to toggle.
    :param bool should_set: Whether to set the flag, or clear it.
    """
    if should_set:
        set_flag(flag)
    else:
        clear_flag(flag)


@cmdline.subcommand()
@cmdline.test_command
def is_flag_set(flag):
    """Assert that a flag is set"""
    return any_flags_set(flag)


@cmdline.subcommand()
@cmdline.test_command
def is_state(state):
    """DEPRECATED Alias for is_flag_set"""
    return is_flag_set(state)


@cmdline.subcommand()
@cmdline.test_command
def all_flags_set(*desired_flags):
    """Assert that all desired_flags are set"""
    active_flags = get_flags()
    return all(flag in active_flags for flag in desired_flags)


@cmdline.subcommand()
@cmdline.test_command
def all_states(*desired_states):
    """DEPRECATED Alias for all_flags_set"""
    return all_flags_set(*desired_states)


@cmdline.subcommand()
@cmdline.test_command
def any_flags_set(*desired_flags):
    """Assert that any of the desired_flags are set"""
    active_flags = get_flags()
    return any(flag in active_flags for flag in desired_flags)


@cmdline.subcommand()
@cmdline.test_command
def any_states(*desired_states):
    """DEPRECATED Alias for any_flags_set"""
    return any_flags_set(*desired_states)


def _expand_replacements(pat, subf, values):
    while any(pat.search(r) for r in values):
        new_values = []
        for value in values:
            m = pat.search(value)
            if not m:
                new_values.append(value)
                continue
            whole_match = m.group(0)
            selected_groups = m.groups()
            for replacement in subf(*selected_groups):
                # have to replace one match at a time, or we'll lose combinations
                # e.g., '{A,B}{A,B}' would turn to ['AA', 'BB'] instead of
                # ['A{A,B}', 'B{A,B}'] -> ['AA', 'AB', 'BA', 'BB']
                new_values.append(value.replace(whole_match, replacement, 1))
        values = new_values
    return values


@cmdline.subcommand()
@cmdline.test_command
def any_hook(*hook_patterns):
    """
    Assert that the currently executing hook matches one of the given patterns.

    Each pattern will match one or more hooks, and can use the following
    special syntax:

      * ``db-relation-{joined,changed}`` can be used to match multiple hooks
        (in this case, ``db-relation-joined`` and ``db-relation-changed``).
      * ``{provides:mysql}-relation-joined`` can be used to match a relation
        hook by the role and interface instead of the relation name.  The role
        must be one of ``provides``, ``requires``, or ``peer``.
      * The previous two can be combined, of course: ``{provides:mysql}-relation-{joined,changed}``
    """
    current_hook = hookenv.hook_name()

    # expand {role:interface} patterns
    i_pat = re.compile(r'{([^:}]+):([^}]+)}')
    hook_patterns = _expand_replacements(i_pat, hookenv.role_and_interface_to_relations, hook_patterns)

    # expand {A,B,C,...} patterns
    c_pat = re.compile(r'{((?:[^:,}]+,?)+)}')
    hook_patterns = _expand_replacements(c_pat, lambda v: v.split(','), hook_patterns)

    return current_hook in hook_patterns


def any_file_changed(filenames, hash_type='md5'):
    """
    Check if any of the given files have changed since the last time this
    was called.

    :param list filenames: Names of files to check. Accepts callables returning
        the filename.
    :param str hash_type: Algorithm to use to check the files.
    """
    changed = False
    for filename in filenames:
        if callable(filename):
            filename = str(filename())
        else:
            filename = str(filename)
        old_hash = unitdata.kv().get('reactive.files_changed.%s' % filename)
        new_hash = host.file_hash(filename, hash_type=hash_type)
        if old_hash != new_hash:
            unitdata.kv().set('reactive.files_changed.%s' % filename, new_hash)
            changed = True  # mark as changed, but keep updating hashes
    return changed


def was_invoked(invocation_id):
    """
    Returns whether the given ID has been invoked before, as per :func:`mark_invoked`.

    This is useful for ensuring that a given block only runs one time::

        def foo():
            if was_invoked('foo'):
                return
            do_something()
            mark_invoked('foo')

    This is also available as a decorator at
    :func:`~charms.reactive.decorators.only_once`.
    """
    return unitdata.kv().get('reactive.invoked.%s' % invocation_id, False)


def mark_invoked(invocation_id):
    """
    Mark the given ID as having been invoked, for use with :func:`was_invoked`.
    """
    unitdata.kv().set('reactive.invoked.%s' % invocation_id, True)


def data_changed(data_id, data, hash_type='md5'):
    """
    Check if the given set of data has changed since the previous call.

    This works by hashing the JSON-serialization of the data.  Note that,
    while the data will be serialized using ``sort_keys=True``, some types
    of data structures, such as sets, may lead to false positivies.

    :param str data_id: Unique identifier for this set of data.
    :param data: JSON-serializable data.
    :param str hash_type: Any hash algorithm supported by :mod:`hashlib`.
    """
    key = 'reactive.data_changed.%s' % data_id
    alg = getattr(hashlib, hash_type)
    serialized = json.dumps(data, sort_keys=True).encode('utf8')
    old_hash = unitdata.kv().get(key)
    new_hash = alg(serialized).hexdigest()
    unitdata.kv().set(key, new_hash)
    return old_hash != new_hash


def _hook(hook_patterns):
    dispatch_phase = unitdata.kv().get('reactive.dispatch.phase')
    return dispatch_phase == 'hooks' and any_hook(*hook_patterns)


def _when_all(flags):
    dispatch_phase = unitdata.kv().get('reactive.dispatch.phase')
    return dispatch_phase == 'other' and all_flags_set(*flags)


def _when_any(flags):
    dispatch_phase = unitdata.kv().get('reactive.dispatch.phase')
    return dispatch_phase == 'other' and any_flags_set(*flags)


def _when_none(flags):
    dispatch_phase = unitdata.kv().get('reactive.dispatch.phase')
    return dispatch_phase == 'other' and not any_flags_set(*flags)


def _when_not_all(flags):
    dispatch_phase = unitdata.kv().get('reactive.dispatch.phase')
    return dispatch_phase == 'other' and not all_flags_set(*flags)
