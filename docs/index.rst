charms.reactive
===============

This module serves as the basis for creating charms and relation
implementations using the reactive pattern.


Overview
--------

Juju is an open source tool for modelling a connected set of applications in a
way that allows for that model to be deployed repeatably and consistently
across different clouds and substrates.  Juju Charms implement the model for
individual applications, their configuration, and the relations between them
and other applications.

In order for the charm to know what actions to take, Juju informs it of
life-cycle events in the form of hooks.  These hooks inform the charm of things
like the initial installation event, changes to charm config, attachment of
storage, and adding and removing of units of related applications.  Because
managing distributed software is difficult and the exact action to take in
response to a life-cycle event can depend on which events have happened in the
past, charms.reactive represents a system for setting flags with semantic
meaning to the charm and then driving behavior off of the combination of those
flags.

The pattern is called "reactive" because you use :func:`@when <charms.reactive.decorators.when>`
and similar decorators to indicate that blocks of code "react" to certain conditions,
such as a relation reaching a specific state, certain config values being set, etc.
More importantly, you can react to not just individual conditions, but meaningful
combinations of conditions that can span multiple hook invocations, in a natural way.

For example, the following would update a config file when both a database
and admin password were available, and, if and only if that file was changed,
the appropriate service would be restarted:

.. code-block:: python

    from charms.reactive import set_flag, clear_flag, when
    from charms.reactive.helpers import any_file_changed
    from charmhelpers.core import templating, hookenv

    @when('db.database.available', 'config.set.admin-pass')
    def render_config(pgsql):
        templating.render('app-config.j2', '/etc/app.conf', {
            'db_conn': pgsql.connection_string(),
            'admin_pass': hookenv.config('admin-pass'),
        })
        if any_file_changed(['/etc/app.conf']):
            set_flag('myapp.restart')

    @when('myapp.restart')
    def restart_service():
        hookenv.service_restart('myapp')
        clear_flag('myapp.restart')


Table of Contents
-----------------

.. toctree::
   :hidden:

   self


.. toctree::
   :glob:
   :maxdepth: 3

   structure
   managed-flags
   layer-basic
   bash-reactive
   faq
   patterns
   api
   internals


.. toctree::
   :caption: Changelog
   :glob:
   :maxdepth: 3

   changelog
