Frequently Asked Questions
==========================

How do I run and debug reactive charm?
--------------------------------------

You run a reactive charm by running a hook in the ``hooks/`` directory. That hook
will start the reactive framework and initiate the "cascade of flags".

The hook files in the ``hooks/`` directory are created by ``layer:basic`` and by
``charm build``. Make sure to include ``layer:basic`` in your `layer.yaml` file if
the hook files aren't present in the `hooks/` directory.

You can find more information about debugging reactive charms in
`the Juju docs <https://docs.jujucharms.com/charm-writing/hook-debug>`_.

.. note:: **Changes to flags are reset when a handler crashes.** Changes to
   flags happen immediately, but they are only persisted at the end of a
   complete and successful run of the reactive framework. All unpersisted
   changes are discarded when a hook crashes.


Why doesn't my Charm do anything? Why are there no hooks in the ``hooks`` directory?
------------------------------------------------------------------------------------

You probably forgot to include :doc:`layer-basic <layer-basic>` in your
``layer.yaml`` file. This layer creates the hook files so that the reactive
framework starts when a hook runs.


How can I react to configuration changes?
-----------------------------------------

The base layer provides :ref:`a set of easy flags <layer-basic/config-flags>`
to react to configuration changes. These flags will be automatically
managed when you include ``layer:basic`` in your ``layer.yaml`` file.

How to remove a flag immediately when a config changes?
----------------------------------------------------------

You can use ``triggers`` for this, see :doc:`triggers` for more info.

Example: clear the flag ``apt.sources_configured`` immediately when the
``install_sources`` config  option changes.

.. code-block:: python

    register_trigger(when='config.changed.install_sources',
                     clear_flag='apt.sources_configured')


How to run a handler even if the flag it reacts to has since been cleared?
--------------------------------------------------------------------------

Take the following case:

.. code-block:: python

    @when('service.stopped')
    def restart_service():
        restart_my_service()
        clear_flag('service.stopped')

    @when_all('service.stopped',
              'endpoint.clients.connected')
    def notify_related_units():
        clients = from_flag('endpoint.clients.connected')
        clients.notify_service_stopped()


The ``notify_related_units`` handler will never get invoked because the
``restart_handler`` will get invoked first and it removes the
``service.stopped`` state. If this is not the desired behavior, if you need to
notify the clients even when the service has been restarted by another handler,
then you can use a ``trigger`` to create a new state specifically for the
``notify_related_units`` handler:


.. code-block:: python

    register_trigger(when='service.stopped',
                     set_flag='clients.need_notification')

    @when('service.stopped')
    def restart_service():
        restart_my_service()
        clear_flag('service.stopped')

    @when_all('clients.need_notification',
              'endpoint.clients.connected')
    def notify_related_units():
        clients = from_flag('endpoint.clients.connected')
        clients.notify_service_stopped()
        clear_flag('clients.need_notification')


See :doc:`triggers` for more information.
