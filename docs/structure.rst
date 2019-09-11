Structure of a Reactive Charm
=============================

A reactive charm is built using layers, with the "top" layer being called
the "charm layer." The charm layer would then reference other layers that it
builds upon, which are generally thought of in two types: base layers, and
interface layers. The charm indicates which layers it builds upon via its
``layer.yaml``, which might look like this:

.. code-block:: yaml

    includes:
      - 'layer:apache'
      - 'interface:mysql'
    options:
      basic:
        # apt packages required by charm code
        packages:
          - 'unzip'

This includes one base layer, ``apache2``, and an interface layer, ``mysql``.
The ``apache2`` layer itself builds upon two other base layers and another
interface layer, so the total hierarchy of the charm would look like this:


.. code-block:: text

                              ┌────────┐
                              │ my_app │
                              └────┬───┘
                         ┌─────────┴─────────┐
                  ┌──────┴────────┐ ┌────────┴────────┐
                  │ layer:apache2 │ │ interface:mysql │
                  └──────┬────────┘ └─────────────────┘
         ┌───────────────┼────────────────┐                
  ┌──────┴──────┐ ┌──────┴────┐ ┌─────────┴──────┐
  │ layer:basic │ │ layer:apt │ │ interface:http │
  └─────────────┘ └───────────┘ └────────────────┘
         

The ``options`` section in the ``layer.yaml`` allows the charm to set
configuration for other layers. In this case, specifying to the ``basic`` layer
that the charm needs the ``unzip`` package in order to function.


Charm Layer
-----------

The charm layer is what most charm authors will be writing, and allows the charm
author to focus on just the information and code which is relevant to the
charm itself. By including other layers, the charm layer can then rely on those
layer to provide common behavior, using documented flags and method calls to
communicate with those layers.

A charm layer consists, at a bare minimum, of the following files:

* ``metadata.yaml``: This file contains information about the charm, such as the
  charm name, summary, description, maintainer, and what relations the charm
  supports.
* ``layer.yaml``: This file indicates what other layers this charm builds upon.
* ``reactive/<charm_name>.py``: This file, where ``<charm_name>`` is replaced by the
  name of the charm (using underscores in place of dashes), is the reactive
  entry point for the charm. It should contain or import files containing all
  of the handlers provided by this charm layer.

The charm layer should also contain a few additional files, though some may be
optional depending on what features the charm supports:

* ``README.md``: This file should document your charm in detail, and is required
  for the charm to be listed in the `Charm Store`_.
* ``copyright``: This file should document what copyright your charm is available
  under.
* ``config.yaml``: For adding configuration_ options to the charm.
* ``icon.svg``: For providing a nice icon for the charm.
* ``actions.yaml`` and ``actions/<action-name>`` scripts: For supporting actions_
  in the charm.
* ``metrics.yaml``: For collecting metrics_ about the deployment.

An example tree for a charm layer might thus look like this:

.. code-block:: text

    .
    ├── README.md
    ├── metadata.yaml
    ├── icon.svg
    ├── config.yaml
    ├── layer.yaml
    ├── reactive/
    │   └── my_app.py
    ├── actions.yaml
    ├── actions/
    │   └── do-something
    └── copyright

.. _configuration: https://jujucharms.com/docs/stable/charms-config
.. _actions: https://jujucharms.com/docs/stable/developer-actions
.. _metrics: https://jujucharms.com/docs/stable/developer-metrics
.. _layers: https://jujucharms.com/docs/stable/authors-charm-building
.. _`Charm Store`: https://jujucharms.com/


Base Layers
-----------

Base layers provide functionality that is common across several charms. These
layers should provide a set of handlers in ``reactive/<layer_name>.py`` which
will set additional flags that will drive behavior in the charm layer. They may
also include a Python module in ``lib/charms/layer/<layer_name>.py`` which can
be imported from the charm layer to provide functions or classes to be used by
the charm layer.

Base layers are otherwise identical to charm layers, and can provide things such
as actions, config options, metrics, etc. for the charm layer.  For example, a
base layer might provide an action script, as well as the corresponding defition
in the ``actions.yaml`` file.  The ``actions.yaml`` file from the charm layer
will then be merged onto the one provided by the base layer, and both sets of
actions will be available.


:doc:`layer:basic <layer-basic>` is a useful base layer:

 - It provides hooks for other layers to react to such as ``install``,
   ``config-changed``, ``upgrade-charm``, and ``update-status``.
 - It provides a :ref:`set of useful flags to react to changing config <layer-basic/config-flags>`.
 - You can tell it to install :ref:`python <layer-basic/wheelhouse.txt>` and :ref:`apt <layer-basic/layer-config>` dependencies of your handlers.


Interface Layers
----------------

Interface layers encapsulate the communication protocol over a Juju interface
when two applications are related together. These layers will react to
applications being related to the charm, and will handle the transfer of data to
and from the units of the related application. This ensures that all charms using
that interface protocol can effectively communicate with one another.

As with base layers, an interface layer will provide a set of flags to inform
the charm layer of the signficant points in the relationship conversation. The
interface layer will also provide a class with well-documented methods to use to
interact with that relation. Instances of these classes will be automatically
created by the framework.

More information about interface layers can be found in `the docs`_.


.. _`the docs`: https://jujucharms.com/docs/stable/developer-layers-interfaces
