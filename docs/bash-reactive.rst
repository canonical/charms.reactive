Reactive with Bash or Other Languages
-------------------------------------

Reactive handlers can be written in any language, provided they conform to
the :class:`~charms.reactive.bus.ExternalHandler` protocol.  In short, they
must accept a ``--test`` and ``--invoke`` argument and do the appropriate
thing when called with each.

There are helpers for writing handlers in bash, which allow you to write
handlers using a decorator-like syntax similar to Python handlers.
For example:

.. code-block:: bash

    #!/bin/bash
    source charms.reactive.sh

    @when 'db.database.available' 'admin-pass'
    function render_config() {
        db_conn=$(relation_call --flag 'db.database.available' connection_string)
        admin_pass=$(config-get 'admin-pass')
        charms.reactive render_template 'app-config.j2' '/etc/app.conf'
    }

    @when_not 'db.database.available'
    function no_db() {
        status-set waiting 'Waiting on database'
    }

    @when_not 'admin-pass'
    function no_db() {
        status-set blocked 'Missing admin password'
    }

    @when_file_changed '/etc/app.conf'
    function restart_service() {
        service myapp restart
    }

    reactive_handler_main

