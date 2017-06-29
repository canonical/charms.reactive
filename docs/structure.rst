
Structure of a Reactive Charm
-----------------------------

The structure of a reactive charm is similar to existing charms, with the
addition of ``reactive`` directory and the ``relations`` directory under
``hooks``:

.. code-block:: text

    .
    ├── metadata.yaml
    ├── reactive
    │   └── common.py
    └── hooks
        ├── pgsql-relation-changed
        └── relations
            └── pgsql
                ├── interface.yaml
                ├── peer.py
                ├── provides.py
                └── requires.py

The hooks will need to call :func:`reactive.main() <charms.reactive.main>`,
and the decorated handler blocks can be placed in any file under the ``reactive``
directory.  Thus, pretty much all of your hooks will end up contain little more
than:

.. code-block:: python

    #!/usr/bin/env python
    from charms.reactive import main
    main()

The ``relations`` directory will contain any interface layer implementations
that your charm uses.

If you are `building a charm with layers`_, as is recommended, both the ``hooks``
and ``relations`` directories will be automatically managed for you by your base
and interface layers, so you can focus on writing handlers under the ``reactive``
directory.

.. _`Building a Charm with Layers`: https://jujucharms.com/docs/stable/authors-charm-building
