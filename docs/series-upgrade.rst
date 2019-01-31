OS Series Upgrades
==================

Upgrades of the operating system's series, or version, are difficult to
automate in a general fashion, so most of the work is done manually by the
operator and the role that the charm plays is somewhat limited.  However, the
charm does need to ensure that during the upgrade, all of the application
services on the unit are disabled and stopped so that nothing runs while the
operator is making changes that could break the application, even if the
machine is rebooted one or more times.

When the operator is about to initiate an OS upgrade, they will run:

.. code-block:: bash

  juju upgrade-series <machine> prepare <target-series>

The framework will then set the ``upgrade.series.in-progress`` flag,  which
will give the charm one and only one chance to disable and stop its application
services in preparation for the upgrade.  Once that flag is set and the charm's
handlers have had a chance to respond, Juju will no longer run any charm code
for the duration of the upgrade.

Once the operator has completed the upgrade, they will run:

.. code-block:: bash

  juju upgrade-series <machine> complete

Juju will once again enable the charm code to run, and the framework will
re-bootstrap the charm environment to ensure that it is setup properly for the
new OS series.  it will then remove the ``upgrade.series.in-progress`` flag.
At this point, the charm should check the new OS series and perform any
necessary migration the application may require to run on the new OS (unless
that was to be performed manually by the operator).  Finally, the charm should
re-enable and start its application services.

Note that it is likely that the charm will need an additional self-managed flag
to track whether the application services were disabled.  The handlers might
look something along the lines of:

.. code-block:: python

  @when('charm.application.started')
  @when('upgrade.series.in-progress')
  def disable_application():
      stop_app_services()
      disable_app_services()
      set_flag('charm.application.disabled')


  @when('charm.application.disabled')
  @when_not('upgrade.series.in-progress')
  def enable_application():
      enable_app_services()
      start_app_services()
      clear_flag('charm.application.disabled')
