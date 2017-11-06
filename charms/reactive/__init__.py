# Copyright 2014-2017 Canonical Limited.
#
# This file is part of charms.reactive
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

import os
import sys

from .flags import set_flag  # noqa
from .flags import clear_flag  # noqa
from .flags import toggle_flag  # noqa
from .flags import register_trigger  # noqa
from .flags import is_flag_set  # noqa
from .flags import all_flags_set  # noqa
from .flags import any_flags_set  # noqa
from .flags import set_state  # noqa  DEPRECATED
from .flags import remove_state  # noqa  DEPRECATED
from .flags import toggle_state  # noqa  DEPRECATED
from .flags import is_state  # noqa  DEPRECATED
from .flags import all_states  # noqa  DEPRECATED
from .flags import get_states # noqa  DEPRECATED
from .flags import any_states  # noqa  DEPRECATED
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
from .decorators import collect_metrics  # noqa
from .decorators import meter_status_changed  # noqa

from . import bus
from . import flags
from . import helpers
from . import relations
from charmhelpers.core import hookenv
from charmhelpers.core import unitdata


# DEPRECATED: transitional imports for backwards compatibility
bus.StateList = flags.StateList
bus.set_state = flags.set_flag
bus.remove_state = flags.clear_flag
bus.get_state = flags.get_state
bus.get_states = flags.get_states
helpers.is_state = flags.is_flag_set
helpers.toggle_state = flags.toggle_flag
helpers.all_states = flags.all_flags_set
helpers.any_states = flags.any_flags_set


# flake8: noqa: C901
def main(relation_name=None):
    """
    This is the main entry point for the reactive framework.  It calls
    :func:`~bus.discover` to find and load all reactive handlers (e.g.,
    :func:`@when <decorators.when>` decorated blocks), and then
    :func:`~bus.dispatch` to trigger handlers until the queue settles out.
    Finally, :meth:`unitdata.kv().flush <charmhelpers.core.unitdata.Storage.flush>`
    is called to persist the flags and other data.

    :param str relation_name: Optional name of the relation which is being handled.
    """
    restricted_mode = hookenv.hook_name() in ['meter-status-changed', 'collect-metrics']

    hookenv.log('Reactive main running for hook %s' % hookenv.hook_name(), level=hookenv.INFO)
    if restricted_mode:
        hookenv.log('Restricted mode.', level=hookenv.INFO)
    # work-around for https://bugs.launchpad.net/juju-core/+bug/1503039
    # ensure that external handlers can tell what hook they're running in
    if 'JUJU_HOOK_NAME' not in os.environ:
        os.environ['JUJU_HOOK_NAME'] = os.path.basename(sys.argv[0])

    if not restricted_mode:
        # update data to be backwards compatible after fix for issue 28
        relations._migrate_conversations()

    if hookenv.hook_name().endswith('-relation-departed'):
        def depart_conv():
            rel = relations.relation_from_name(hookenv.relation_type())
            rel.conversation().depart()
        hookenv.atexit(depart_conv)

    if restricted_mode:  # limit what gets run in restricted mode
        def done():
            unitdata._KV.flush()
    else:
        def done():
            hookenv._run_atexit()
            unitdata._KV.flush()

    try:
        bus.discover()
        if not restricted_mode:  # limit what gets run in restricted mode
            hookenv._run_atstart()
        bus.dispatch(restricted=restricted_mode)
    except SystemExit as x:
        if x.code is None or x.code == 0:
            done()
        raise
    done()
