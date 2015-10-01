from .bus import set_state  # noqa
from .bus import remove_state  # noqa
from .helpers import toggle_state  # noqa
from .helpers import is_state  # noqa
from .helpers import all_states  # noqa
from .relations import scopes  # noqa
from .relations import RelationBase  # noqa
from .decorators import hook  # noqa
from .decorators import when  # noqa
from .decorators import when_not  # noqa
from .decorators import not_unless  # noqa
from .decorators import only_once  # noqa

from . import bus
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

    def flush_kv():
        if unitdata._KV:
            unitdata._KV.flush()
    hookenv.atexit(flush_kv)
    try:
        bus.discover()
        bus.dispatch()
    except SystemExit as x:
        if x.code is None or x.code == 0:
            hookenv._run_atexit()
        raise
    hookenv._run_atexit()
