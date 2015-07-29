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

import json
import hashlib

from charmhelpers.core import host
from charmhelpers.core import unitdata
from charms.reactive.bus import any_hook
from charms.reactive.bus import all_states
from charms.reactive.bus import StateWatch


def any_file_changed(filenames, hash_type='md5'):
    """
    Check if any of the given files have changed since the last time this
    was called.

    :param list filenames: Names of files to check.
    :param str hash_type: Algorithm to use to check the files.
    """
    changed = False
    for filename in filenames:
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
    :func:`~charmhelpers.core.reactive.decorators.only_once`.
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


def _when(handler_id, states, invert):
    dispatch_phase = unitdata.kv().get('reactive.dispatch.phase')
    return dispatch_phase == 'other' and StateWatch.watch(handler_id, states) and (all_states(*states) ^ invert)
