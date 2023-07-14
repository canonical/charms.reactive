Charms.Reactive
---------------

This module serves as the basis for creating charms and relation
implementations using the reactive pattern. You can see its goal and vision in
`the vision document`_

The full documentation is available online at: https://charmsreactive.readthedocs.io/

.. _the vision document: https://github.com/juju-solutions/charms.reactive/blob/master/VISION.md

Status - Deprecated
-------------------

Please don't use ``charms.reactive`` for new charms. This library is being
maintained for existing ``charms.reactive`` charms, to allow bug fixes to be
made and to enable them to be built with `charm-tools
<https://github.com/juju-solutions/charms.reactive>`_ using the reactive plugin
in `charmcraft <https://github.com/canonical/charmcraft>`_.

If you are going to write a new charm, then your life, and code, will be much
easier with an `Operator Framework <https://juju.is/about>`_ charm.

Usage
-----

See `Building a Charm from Layers`_ for more information on how to use the
charms.reactive framework. Also look at the `layer-basic documentation`_ for more
info on how to use the basic layer.

.. _Building a Charm from Layers: https://web.archive.org/web/20160319143647/https://jujucharms.com/docs/stable/authors-charm-building
.. _layer-basic documentation: https://github.com/juju-solutions/layer-basic/blob/master/README.md

Contributing
------------

Want to contribute? Great! We're looking forward to your Pull Request. See
`HACKING.md`_ for more information about how to contribute to charmhelpers.

.. _HACKING.md: https://github.com/juju-solutions/charms.reactive/blob/master/HACKING.md
