.. _automatic-flags:

Automatic Flags
===============

The reactive framework will automatically set some flags for your charm,
based on lifecycle events from Juju.  These flags can inform your charm
of things such as upgrades, config changes, relation activity, etc.

With a few exceptions, these flags will be set by the framework but it is up
to your charm to clear them, if need be.  To avoid conflicts between layers,
it is recommended that only the top-level charm layer (or interface layer, in
the case of endpoint flags) use any of the automatic flags directly; any base 
layer should instead use :func:`~charms.reactive.flags.register_trigger` to
"wrap" the automatic flag with a layer-specific flag that can be safely used
within that layer.

The flags that are set by the framework are:

+----------------------------------------------+------------------------------------------------------------+
| ``upgrade.charm.completed``                  | This is set when a new revision of the charm               |
|                                              | code has landed on the unit.                               |
+----------------------------------------------+------------------------------------------------------------+
| ``upgrade.resources.check``                  | This is set when new versions of charm resources may be    |
|                                              | available, as indicated by the ``upgrade-charm`` hook      |
|                                              | having been called.  However, to avoid fetching and        |
|                                              | storing resources unnecessarily, no resources are          |
|                                              | actually checked, so you will need to use                  |
|                                              | :func:`~charms.reactive.helpers.resource_changed` or       |
|                                              | :func:`~charms.reactive.helpers.any_resource_changed`      |
|                                              | to determine which, if any, resources were actually        |
|                                              | updated.                                                   |
+----------------------------------------------+------------------------------------------------------------+
| ``upgrade.series.started``                   | This is set when the ``pre-series-upgrade`` hook is        |
|                                              | fired, indicating that any application services should     |
|                                              | be stopped and disabled so that they do not start on       |
|                                              | reboot, so that the operator can perform a OS series       |
|                                              | upgrade.                                                   |
+----------------------------------------------+------------------------------------------------------------+
| ``upgrade.series.completed``                 | This is set when the ``post-series-upgrade`` hook is       |
|                                              | fired, indicating that the operator has completed the      |
|                                              | series upgrade and any application migrations should be    |
|                                              | performed and any services should be resumed and           |
|                                              | re-enabled.                                                |
+----------------------------------------------+------------------------------------------------------------+
| ``config.changed``                           | This is set when any config option has changed.            |
+----------------------------------------------+------------------------------------------------------------+
| ``config.changed.{option_name}``             | This is set for each config option that has changed.       |
+----------------------------------------------+------------------------------------------------------------+
| ``config.set.{option_name}``                 | This is set for each config option whose value is not      |
|                                              | ``None``, ``False``, or an empty string.                   |
+----------------------------------------------+------------------------------------------------------------+
| ``config.default.{option_name}``             | This is set for each config option whose value was         |
|                                              | changed from its default.                                  |
+----------------------------------------------+------------------------------------------------------------+
| ``leadership.is_leader``                     | This is set when the unit is the leader. The unit will     |
|                                              | remain the leader for the remainder of the hook, but       |
|                                              | may not be leader in future hooks.                         |
+----------------------------------------------+------------------------------------------------------------+
| ``leadership.changed``                       | This is set when any leadership setting has changed.       |
+----------------------------------------------+------------------------------------------------------------+
| ``leadership.changed.{setting_name}``        | This is set for each leadership setting that has           |
|                                              | changed.                                                   |
+----------------------------------------------+------------------------------------------------------------+
| ``leadership.set.{setting_name}``            | This is set for each leadership setting that has been      |
|                                              | to set to a value other than ``None``.                     |
+----------------------------------------------+------------------------------------------------------------+
| ``endpoint.{endpoint_name}.joined``          | This is set when a relation is joined on an endpoint. [1]_ |
+----------------------------------------------+------------------------------------------------------------+
| ``endpoint.{endpoint_name}.changed``         | This is set when relation data has changed. [1]_           |
+----------------------------------------------+------------------------------------------------------------+
| ``endpoint.{endpoint_name}.changed.{field}`` | This is set for each field of relation data which has      |
|                                              | changed. [1]_                                              |
+----------------------------------------------+------------------------------------------------------------+
| ``endpoint.{endpoint_name}.departed``        | This is set when a unit leaves a relation. [1]_            |
+----------------------------------------------+------------------------------------------------------------+

.. [1]

  See :class:`~charms.reactive.endpoints.Endpoint` for more information
  on the ``endpoint.{endpoint_name}.*`` flags.

.. note::

  The behaivor of the leadership and config flags when managed by this library
  differs slightly from when they are managed by the leadership and basic
  layer, respectively.  Specifically, those layers perform automatic removal
  of the flags at the end of the hook context in which they are set, while
  this library does not.

  If the leadership layer is included, or if the basic layer's
  ``autoremove_config_flags`` option is set to ``true`` (currently the
  default), then those layers will take precedence over this layer and the
  flags will be automatically removed.  It is recommended, however, that
  charms move toward using triggers and removing the flags manually in the
  charm layer.
