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
import sys

from .bus import set_state  # noqa
from .bus import remove_state  # noqa
from .helpers import toggle_state  # noqa
from .helpers import is_state  # noqa
from .helpers import all_states  # noqa
from .relations import scopes  # noqa
from .relations import RelationBase  # noqa
from .decorators import hook  # noqa
from .decorators import when  # noqa
from .decorators import when_all  # noqa
from .decorators import when_any  # noqa
from .decorators import when_not  # noqa
from .decorators import when_none  # noqa
from .decorators import when_not_all  # noqa
from .decorators import not_unless  # noqa
from .decorators import only_once  # noqa
from .decorators import when_file_changed  # noqa

from . import bus
from . import relations
from charmhelpers.core import hookenv
from charmhelpers.core import unitdata


def main(relation_name=None):
    """
    This is the main entry point for the reactive framework.  It calls
    :func:`~bus.discover` to find and load all reactive handlers (e.g.,
    :func:`@when <decorators.when>` decorated blocks), and then
    :func:`~bus.dispatch` to trigger hook and state handlers until the
    state settles out.  Finally,
    :meth:`unitdata.kv().flush <charmhelpers.core.unitdata.Storage.flush>`
    is called to persist the state.

    :param str relation_name: Optional name of the relation which is being handled.
    """
    hookenv.log('Reactive main running for hook %s' % hookenv.hook_name(), level=hookenv.INFO)

    # work-around for https://bugs.launchpad.net/juju-core/+bug/1503039
    # ensure that external handlers can tell what hook they're running in
    if 'JUJU_HOOK_NAME' not in os.environ:
        os.environ['JUJU_HOOK_NAME'] = os.path.basename(sys.argv[0])

    # update data to be backwards compatible after fix for issue 28
    relations._migrate_conversations()

    def flush_kv():
        if unitdata._KV:
            unitdata._KV.flush()
    hookenv.atexit(flush_kv)
    if hookenv.hook_name().endswith('-relation-departed'):
        def depart_conv():
            rel = RelationBase.from_name(hookenv.relation_type())
            rel.conversation().depart()
        hookenv.atexit(depart_conv)
    try:
        bus.discover()
        hookenv._run_atstart()
        bus.dispatch()
    except SystemExit as x:
        if x.code is None or x.code == 0:
            hookenv._run_atexit()
        raise
    hookenv._run_atexit()
