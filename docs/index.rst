charms.reactive
===============

This module serves as the basis for creating charms and relation
implementations using the reactive pattern.


Overview
--------

The pattern is "reactive" because you use :func:`@when <charms.reactive.decorators.when>`
and similar decorators to indicate that blocks of code react to certain conditions,
such as a relation reaching a specific `state`, a file changing, certain config
values being set, etc.  More importantly, you can react to not just indvidual
conditions, but meaningful combinations of conditions that can span multiple hook
invocations, in a natural way.

For example, the following would update a config file when both a database
and admin password were available, and, if and only if that file was changed,
the appropriate service would be restarted:

.. code-block:: python

    @when('db.database.available', 'admin-pass')
    def render_config(pgsql):
        render_template('app-config.j2', '/etc/app.conf', {
            'db_conn': pgsql.connection_string(),
            'admin_pass': hookenv.config('admin-pass'),
        })

    @when_file_changed('/etc/app.conf')
    def restart_service():
        hookenv.service_restart('myapp')

    if __name__ == '__main__':
        reactive.main()


Structure of a Reactive Charm
-----------------------------

The structure of a reactive charm is similar to existing charms, with the
addition of ``reactive`` and ``relations`` directories under ``hooks``:

.. code-block:: text

    .
    ├── metadata.yaml
    ├── reactive
    │   └── common.py
    └── hooks
        ├── pgsql-relation-changed
        └── relations
            └── pgsql
                ├── interface.yaml
                ├── peer.py
                ├── provides.py
                └── requires.py

The hooks will need to call :func:`reactive.main() <charms.reactive.main>`,
and the decorated handler blocks can be placed in any file under the ``reactive``
directory.  The ``relations`` directory can contain any relation stub implementations
that your charm uses.

If using Charm Composition, as is recommended, the ``hooks`` and ``relations``
directories will be automatically managed for you by your base layer and
relation stubs, so you can focus on writing handlers under the ``reactive``
directory.


Discovery and Dispatch of Reactive Handlers
-------------------------------------------

Reactive handlers are loaded from any file under the ``reactive`` directory,
as well as any relation stubs you are using.  Handlers can be decorated blocks
in Python, or executable files following the :class:`~charms.reactive.bus.ExternalHandler`
protocol.  Handlers can be split amongst several files, which is particularly
useful for layers, as each layer can define its own file containing handlers
so as not to conflict with files from other layers.

Once all of the handlers are loaded, all :func:`@hook <charms.reactive.decorators.hook>`
handlers will be executed, in a non-determined order.  In general, only one layer
or relation stub should have a matching :func:`@hook <charms.reactive.decorators.hook>`
block for each hook, which should then set appropriate semantically meaningful
states that the other layers can react to.  If there are multiple handlers that
match for a given hook, there is no guarantee which order they will execute in.
Hook handlers should live in the layer that is most appropriate for them.  The
base or runtime layer will probably handle the install and upgrade hooks, relation
stubs will handle all of the relation hooks, etc.

After all of the hook handlers have run, other handlers are dispatched based
on the states set by the hook handlers and any states from previous runs.
States can be thought of as persistent events.  Various hook invocations
can each set their appropriate states, and the reactive handlers will be
triggered when all of the appropriate states are set, regardless of when
and in which order they are each set.

All handlers are tested and matching handlers queued before invoking the
first handler.  Thus, states set by a handler will not trigger new matching
handlers until after all of the current set of matching handlers are done.
This allows you to ensure some ordering of otherwise non-determined handler
invocation by chaining states (e.g., handler_A sets state_B, which triggers
handler_B which then sets state_C, which triggers handler_C, and so on).

Note, however, that removing a state causes the remaining set of matched handlers
to be re-tested.  This ensures that a handler is never invoked when the state is
no longer active.


Relation Stubs
--------------

A big part of the reactive pattern is the use of relation stubs.  These are
classes, based on :class:`~charms.reactive.relations.RelationBase`,
that are reponsible for managing the conversation with remote services or units
and informing the charm when the conversation has reached key points, called
states, upon which the charm can act and do useful work.  They allow a single
interface author to create code to handle both sides of the conversation, and
to expose a well-defined API to charm authors.

Relation stubs allows charm authors to focus on implementing the behavior and
resources that the relation provides, while the interface author focuses on the
communication necessary to get that behavior and resources between the related
services.  In general, the author of the charm that provides a particular
interface is likely to be the interface author that creates both the provides
and requires sides of the relation.  After that, charm authors that wish to
make use of that interface can just re-use the existing relation stub.


Non-Python Reactive Handlers
----------------------------

Reactive handlers can be written in any language, provided they conform to
the :class:`~charms.reactive.bus.ExternalHandler` protocol.  In short, they
must accept a ``--test`` and ``--invoke`` argument and do the appropriate
thing when called with each.

There are helpers for writing handlers in bash.  For example:

.. code-block:: bash

    #!/bin/bash
    source $CHARM_DIR/bin/charms.reactive.sh

    @when 'db.database.available' 'admin-pass'
    function render_config() {
        db_conn=$(state_relation_call 'db.database.available' connection_string)
        admin_pass=$(config-get 'admin-pass')
        charms.reactive render_template 'app-config.j2' '/etc/app.conf'
    }

    @when_not 'db.database.available'
    function no_db() {
        status-set waiting 'Waiting on database'
    }

    @when_not 'admin-pass'
    function no_db() {
        status-set blocked 'Missing admin password'
    }

    @when_file_changed '/etc/app.conf'
    function restart_service() {
        service myapp restart
    }

    reactive_handler_main



Reactive API Documentation
--------------------------


.. toctree::

    charms.reactive.decorators
    charms.reactive.helpers
    charms.reactive.relations
    charms.reactive.bus

.. automodule:: charms.reactive
    :members:
    :undoc-members:
    :show-inheritance:
