Reactive Triggers
=================


Coupling Flags with Triggers
----------------------------

In general, it is best to be explicit about setting or clearing a flag.  This
makes the code more maintainable and easier to follow and reason about.
However, rarely, due to the fact that handlers for a given flag are
independent and thus there are no guarantees about the order in which they may
execute, it is sometimes necessary to enforce that two flags must be set at
the same time or that one must be cleared if the other is set.

As an example of when this might be necessary, consider a charm which provides
two config values, one that determines the location from which resources should
be fetched, with a default location provided by the charm, and another which
indicates that a particular feature be installed and enabled.  If the charm is
deployed and fetches all of the resources, it might set a flag that indicates
that all resources are available and any installation can proceed.  However, if
both resource location and feature flag config options are changed at the same
time, the handlers might be invoked in an order that causes the feature
installation to happen before the resource change has been observed, leading to
the feature using the wrong resource.  This problem is particularly intractable
if the layer managing the resource location and readiness options is different
than the layer managing the feature option, such as with the apt layer.

Triggers provide a mechanism for a flag to indicate that when a particular flag
is set, another specific flag should be either set or cleared.  To use a
trigger, you simply have to register it, which can be done from inside a
handler, or at the top level of your handlers file:

.. code-block:: python

    from charms.reactive.flags import register_trigger
    from charms.reactive.flags import set_flag
    from charms.reactive.decorators import when


    register_trigger(when='flag_a',
                     set_flag='flag_b')


    @when('flag_b')
    def handler():
        do_something()
        register_trigger(when='flag_a',
                         clear_flag='flag_c')
        set_flag('flag_c')


When a trigger is registered, then as soon as the flag given by ``when`` is
set, the other flag is set or cleared at the same time.  Thus, there is no
chance that another handler will run in between.

Keep in mind that since triggers are implicit, they should be used sparingly.
Most use cases can be better modeled by explicitly setting and clearing flags.


Example uses of triggers
------------------------

**Remove flags immediately when config changes**

In the ``apt`` layer, the ``install_sources`` config option specifies which
repositories and ppa's to use for installing a package, so these need to be
added before installing any package. This is easy to do with flags: you create
a handler that adds the sources and then sets the flag
``apt.sources_configured``. The handler that installs the packages reacts to
that flag with ``@when('apt.sources_configured')``. This works perfectly the
first time but what happens if the ``install_sources`` config option gets
changed after they are first configured? Then the ``apt.sources_configured``
flag needs to be cleared immediately before any new packages are installed.
This is where triggers come in: You create a trigger that unsets the
`apt.sources_configured` flag when the `install_sources` config changes.


.. code-block:: python

    register_trigger(when='config.changed.install_sources',
                     clear_flag='apt.sources_configured')


    @when_not('apt.sources_configured')
    def sources_handler():
        configure_sources()
        set_state('apt.sources_configured')


    @when_all('apt.needs_update',
              'apt.sources_configured')
    def update():
        charms.apt.update()
        clear_flag('apt.sources_configured')


    @when('apt.queued_installs')
    @when_not('apt.needs_update')
    def install_queued():
        charms.apt.install_queued()
        clear_flag('apt.queued_installs')


    @when_not('apt.queued_installs')
    def ensure_package_status():
       charms.apt.ensure_package_status()
