Frequently Asked Questions
==========================

How do I run and debug reactive charm?
-----------------------------------

You run a reactive charm by running a hook in the `hooks/` directory. That hook
will start the reactive framework and initiate the "cascade of states".

The hook files in the `hooks/` directory are created by `layer-basic` and by
`charm build`. Make sure to include `layer-basic` in your `layer.yaml` file if
the hook files aren't present in the `hooks/` directory.

You can find more information about debugging reactive charms in
`the Juju docs <https://jujucharms.com/docs/2.2/developer-debugging>`_.
