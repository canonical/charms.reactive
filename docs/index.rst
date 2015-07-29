charmhelpers.core.reactive
==========================

This module serves as the basis for creating charms and relation
implementations using the reactive pattern.


Overview
--------

The pattern is "reactive" because you use :func:`@when <charmhelpers.core.reactive.decorators.when>`
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
addition of ``reactive`` and ``relations`` directories under ``hooks``::

    .
    ├── metadata.yaml
    └── hooks
        ├── pgsql-relation-changed
        ├── reactive
        │   └── common.py
        └── relations
            └── pgsql
                ├── common
                │   └── __init__.py
                ├── interface.yaml
                ├── peer.py
                ├── provides.py
                └── requires.py

The hooks will need to call :func:`reactive.main() <charmhelpers.core.reactive.main>`,
and the decorated handler blocks can be placed in any file under the ``reactive``
directory.  The ``relations`` directory can contain any relation stub implementations
that your charm uses.

If using Charm Composition, as is recommended, the relation hooks and ``relations``
directories will be automatically managed for you based on your ``metadata.yaml``,
so you can focus on writing just the ``install`` and ``config-changed`` hooks, and
the ``reactive`` handler files.


Relation Stubs
--------------

A big part of the reactive pattern is the use of relation stubs.  These are
classes, based on :class:`~charmhelpers.core.reactive.relations.RelationBase`,
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
the :class:`~charmhelpers.core.bus.ExternalHandler` protocol.  In short, they
must accept a ``--test`` and ``--invoke`` argument and do the appropriate
thing when called with each.

There are helpers for writing handlers in bash.  For example:

.. code-block:: bash

    source `which reactive.sh`

    @when 'db.database.available' 'admin-pass'
    function render_config() {
        db_conn=$(state_relation_call 'db.database.available' connection_string)
        admin_pass=$(config-get 'admin-pass')
        chlp render_template 'app-config.j2' '/etc/app.conf' --db_conn="$db_conn" --admin_pass="$admin_pass"
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
