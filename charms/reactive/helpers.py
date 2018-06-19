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
from pathlib import Path

from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core import unitdata
from charmhelpers.cli import cmdline
from charms.reactive.flags import any_flags_set, all_flags_set
from charms.reactive.flags import set_flag, toggle_flag
# import deprecated functions for backwards compatibility
from charms.reactive.flags import is_state, all_states, any_states  # noqa


__all__ = [
    'data_changed',
    'file_changed',
    'any_file_changed',
    'resource_changed',
    'any_resource_changed',
    'leader_set',
    'leader_get',
]


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


def file_changed(filename, hash_type):
    """
    Check if the given file has changed since the last time this was called.

    :param str filename: Name of file to check. Accepts a callable returning
        the filename.
    :param str hash_type: Algorithm to use to check the files.
    """
    if callable(filename):
        filename = str(filename())
    else:
        filename = str(filename)
    old_hash = unitdata.kv().get('reactive.files_changed.%s' % filename)
    new_hash = host.file_hash(filename, hash_type=hash_type)
    unitdata.kv().set('reactive.files_changed.%s' % filename, new_hash)
    return old_hash != new_hash


def any_file_changed(filenames, hash_type='md5'):
    """
    Check if any of the given files have changed since the last time this
    was called.

    :param list filenames: Names of files to check. Accepts callables returning
        the filename.
    :param str hash_type: Algorithm to use to check the files.
    """
    return any([file_changed(filename, hash_type) for filename in filenames])


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


def resource_changed(resource_name, hash_type='md5'):
    """
    Check if the given resource has changed since the previous call.

    This works by using :func:`~charms.reactive.helpers.file_changed` on the
    result of resource_get_.  Note that calling this will fetch the resource
    from the controller if it hasn't been already, incuring network and disk
    usage.

    If the resource is an empty (zero-byte) file, if the resource can't be
    fetched, or if resources are not supported on the current controller
    version, it will return ``None`` instead of ``True`` or ``False``.

    :param str resource_name: Name of a resource defined in ``metadata.yaml``.
    :param str hash_type: Any hash algorithm supported by :mod:`hashlib`.

    :returns: ``True``, ``False``, or ``None``.

    .. _resource_get: https://charm-helpers.readthedocs.io/en/latest/api/charmhelpers.core.hookenv.html#charmhelpers.core.hookenv.resource_get
    """
    try:
        resource_file = hookenv.resource_get(resource_name)
        if resource_file is False:
            return None
        if Path(resource_file).stat().st_size == 0:
            return None
        return file_changed(resource_file, hash_type)
    except NotImplementedError:
        return None


def any_resource_changed(resource_names, hash_type='md5'):
    """
    Check if any of the named resources have changed, using
    :func:`~charms.reactive.helpers.resource_changed`.

    :param list resource_names: List of resource names to check.
    :param str hash_type: Any hash algorithm supported by :mod:`hashlib`.

    :returns: ``True`` if any resource has changed, ``False`` if no resource
        has changed, or ``None`` if any resource cannot be fetched or were
        empty and none that could be fetched have changed.
    """
    results = [resource_changed(resource_name, hash_type)
               for resource_name in resource_names]
    if any(results):
        return True
    elif None in results:
        return None
    else:
        return False


def leader_set(*args, **kw):
    """
    Change leadership settings, ensuring that the leadership flags are updated.

    Settings may either be passed in as a single dictionary, or using keyword
    arguments. All values must be strings.

    The ``leadership.set.{setting_name}`` flag will be set if the value is not
    ``None``.

    Changed leadership settings will set the ``leadership.changed.{setting_name}``
    and ``leadership.changed`` flags.

    These flag changes take effect immediately on the leader, and
    in future hooks run on non-leaders. In this way both leaders and
    non-leaders can share handlers, waiting on these flags.  Note that if you
    use charmhelpers's leader_set_ directly, other handlers on the
    leader may never be notified of the change.

    See :ref:`automatic-flags` for more information on the managed flags.

    .. _leader_set: https://charm-helpers.readthedocs.io/en/latest/api/charmhelpers.core.hookenv.html#charmhelpers.core.hookenv.leader_set
    """
    if args:
        if len(args) > 1:
            raise TypeError('leader_set() takes 1 positional argument but '
                            '{} were given'.format(len(args)))
        else:
            settings = dict(args[0])
    else:
        settings = {}
    settings.update(kw)
    previous = unitdata.kv().getrange('leadership.settings.', strip=True)

    for key, value in settings.items():
        if value != previous.get(key):
            set_flag('leadership.changed.{}'.format(key))
            set_flag('leadership.changed')
        toggle_flag('leadership.set.{}'.format(key), value is not None)
    hookenv.leader_set(settings)
    unitdata.kv().update(settings, prefix='leadership.settings.')


def leader_get(attribute=None):
    '''Return leadership settings, per charmhelpers.core.hookenv.leader_get.'''
    return hookenv.leader_get(attribute)


def _hook(hook_patterns):
    dispatch_phase = unitdata.kv().get('reactive.dispatch.phase')
    return dispatch_phase == 'hooks' and any_hook(*hook_patterns)


def _restricted_hook(hook_name):
    current_hook = hookenv.hook_name()
    dispatch_phase = unitdata.kv().get('reactive.dispatch.phase')
    return dispatch_phase == 'restricted' and current_hook == hook_name


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
