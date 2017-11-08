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
`the Juju docs <https://jujucharms.com/docs/2.2/developer-debugging>`_.

.. note:: **Changes to flags are reset when a handler crashes.** Changes to
   flags happen immediately, but they are only persisted at the end of a
   complete and successful run of the reactive framework. All unpersisted
   changes are discarded when a hook crashes.


Why doesn't my Charm do anything? Why are there no hooks in the ``hooks`` directory?
------------------------------------------------------------------------------------

You probably forgot to include
`layer:basic <https://github.com/juju-solutions/layer-basic>`_ in your
``layer.yaml`` file. This layer creates the hook files so that the reactive
framework starts when a hook runs.


How can I react to configuration changes?
-----------------------------------------

`layer:basic <https://github.com/juju-solutions/layer-basic>`_ provides a set
of easy flags to react to configuration changes. The following flags will be
automatically managed when you include ``layer:basic`` in your ``layer.yaml`` file.

``layer:basic`` will manage the following flags:

  * ``config.changed``  Any config option has changed from its previous value.
    This flag is cleared automatically at the end of each hook invocation.

  * ``config.changed.<option>`` A specific config option has changed.
    ``<option>`` will be replaced by the config option name from ``config.yaml``.
    This flag is cleared automatically at the end of each hook invocation.

  * ``config.set.<option>`` A specific config option has a True or non-empty
    value set.  ``<option>`` will be replaced by the config option name from
    ``config.yaml``. This flag is cleared automatically at the end of each hook
    invocation.

  * ``config.default.<option>`` A specific config option is set to its
    default value.  ``option>`` will be replaced by the config option name
    from ``config.yaml``.  This flag is cleared automatically at the end of
    each hook invocation.
