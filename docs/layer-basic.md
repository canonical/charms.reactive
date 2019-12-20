# The base layer: layer-basic

<a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="Apache 2.0 License"></a>

This is the base layer for all reactive Charms. It provides all of the standard
Juju hooks and starts the reactive framework when these hooks get executed. It
also bootstraps the [charm-helpers][] and `charms.reactive` libraries, and all
of their dependencies for use by the Charm. Check out the
[code for the basic layer on Github][layer-basic].


## Usage

To create a charm layer using this base layer, you need only include it in
a `layer.yaml` file.

```yaml
includes: ['layer:basic']
```

This will fetch this layer from [interfaces.juju.solutions][] and incorporate
it into your charm layer. You can then add handlers under the `reactive/`
directory. Note that **any** file under `reactive/` will be expected to
contain handlers, whether as Python decorated functions or [executables][non-python]
using the [external handler protocol][external handler protocol].


## Hooks

This layer provides a `hook.template` which starts the reactive framework when
the hook is run.  During the build process, this template is used to implement
all of the following hooks, as well as any necessary relation and storage hooks:

  * `config-changed`
  * `install`
  * `leader-elected`
  * `leader-settings-changed`
  * `start`
  * `stop`
  * `upgrade-charm`
  * `update-status`
  * `pre-series-upgrade`
  * `post-series-upgrade`

A layer can implement other hooks (e.g., `metrics`) by putting them in the `hooks`
directory.

```eval_rst
.. note:: Because ``update-status`` is invoked every 5 minutes, you should take
   care to ensure that your reactive handlers only invoke expensive operations
   when absolutely necessary.  It is recommended that you use helpers like
   :func:`data_changed <charms.reactive.helpers.data_changed>` to ensure
   that handlers run only when necessary.
```

```eval_rst
.. note:: The `charm snap <https://snapcraft.io/charm>`_ has been the supported
   way to build charms for a long time, but there is still an old version of
   charm-tools available via apt on some systems.  This old version doesn't
   properly handle the ``hook.template`` file, leading to missing hooks when
   charms are built.  If you encounter this issue, please make sure you have
   the snap installed and remove any copies of the ``charm`` or ``charm-tools``
   apt packages.
```


```eval_rst
.. _layer-basic/config-flags:
```
## Reactive flags for Charm config

This layer will set the following flags:

  * **`config.changed`**  Any config option has changed from its previous value.
    This flag is cleared automatically at the end of each hook invocation.

  * **`config.changed.<option>`** A specific config option has changed.
    **`<option>`** will be replaced by the config option name from `config.yaml`.
    This flag is cleared automatically at the end of each hook invocation.

  * **`config.set.<option>`** A specific config option has a True or non-empty
    value set.  **`<option>`** will be replaced by the config option name from
    `config.yaml`. This flag is cleared automatically at the end of each hook
    invocation.

  * **`config.default.<option>`** A specific config option is set to its
    default value.  **`<option>`** will be replaced by the config option name
    from `config.yaml`. This flag is cleared automatically at the end of
    each hook invocation.

An example using the config flags would be:

```python
@when('config.changed.my-opt')
def my_opt_changed():
    update_config()
    restart_service()
```


```eval_rst
.. _layer-basic/layer-config:
```
## Layer Configuration

This layer supports the following options, which can be set in `layer.yaml`:

  * **packages**  A list of system packages to be installed before the reactive
    handlers are invoked.
    ```eval_rst
    .. note:: The ``packages`` layer option is intended for **charm** dependencies only.
       That is, for libraries and applications that the charm code itself needs to
       do its job of deploying and configuring the payload. If the payload (the
       application you're deploying) itself has dependencies, those should be
       handled separately, by your Charm using for example the
       `Apt layer <https://github.com/stub42/layer-apt>`_
    ```

  * **python_packages**  A list of Python packages to be installed after the wheelhouse
    but before the reactive handlers are invoked.
    ```eval_rst
    .. note:: The ``packages`` layer option is intended for **charm** dependencies only.
       That is, for libraries and applications that the charm code itself needs to
       do its job of deploying and configuring the payload. If the payload (the
       application you're deploying) itself has dependencies, those should be
       handled separately, by your Charm using for example the
       `Apt layer <https://github.com/stub42/layer-apt>`_
    ```

  * **use_venv**  If set to true, the charm dependencies from the various
    layers' `wheelhouse.txt` files will be installed in a Python virtualenv
    located at `$JUJU_CHARM_DIR/../.venv`.  This keeps charm dependencies from
    conflicting with payload dependencies, but you must take care to preserve
    the environment and interpreter if using `execl` or `subprocess`.

  * **include_system_packages**  If set to true and using a venv, include
    the `--system-site-packages` options to make system Python libraries
    visible within the venv.

An example `layer.yaml` using these options might be:

```yaml
includes: ['layer:basic']
options:
  basic:
    packages: ['git']
    use_venv: true
    include_system_packages: true
```


```eval_rst
.. _layer-basic/wheelhouse.txt:
```
## Wheelhouse.txt for Charm Python dependencies

`layer-basic` provides two methods to install dependencies of your charm code:
`wheelhouse.txt` for python dependencies and the `packages` layer option for
apt dependencies.


Each layer can include a `wheelhouse.txt` file with Python requirement lines.
*The format of this file is the same as pip's [`requirements.txt`][] file.*
For example, this layer's `wheelhouse.txt` includes:

```
pip>=7.0.0,<8.0.0
charmhelpers>=0.4.0,<1.0.0
charms.reactive>=0.1.0,<2.0.0
```

All of these dependencies from each layer will be fetched (and updated) at build
time and will be automatically installed by this base layer **before any
reactive handlers are run.**

See [PyPI][pypi charms.X] for packages under the `charms.` namespace which might
be useful for your charm. See the `packages` layer option of this layer for
installing ``apt`` dependencies of your Charm code.

```eval_rst
.. note:: The ``wheelhouse.yaml`` are intended for **charm** dependencies only.
   That is, for libraries and applications that the charm code itself needs to
   do its job of deploying and configuring the payload. If the payload (the
   application you're deploying) itself has dependencies, those should be
   handled separately.
```

## Exec.d Support

It is often necessary to configure and reconfigure machines
after provisioning, but before attempting to run the charm.
Common examples are specialized network configuration, enabling
of custom hardware, non-standard disk partitioning and filesystems,
adding secrets and keys required for using a secured network.

The reactive framework's base layer invokes this mechanism as
early as possible, before any network access is made or dependencies
unpacked or non-standard modules imported (including the charms.reactive
framework itself).

Operators needing to use this functionality may branch a charm and
create an exec.d directory in it. The exec.d directory in turn contains
one or more subdirectories, each of which contains an executable called
charm-pre-install and any other required resources. The charm-pre-install
executables are run, and if successful, state saved so they will not be
run again.

```
$JUJU_CHARM_DIR/exec.d/mynamespace/charm-pre-install
```

An alternative to branching a charm is to compose a new charm that contains
the exec.d directory, using the original charm as a layer,

A charm author could also abuse this mechanism to modify the charm
environment in unusual ways, but for most purposes it is saner to use
`charmhelpers.core.hookenv.atstart()`.


## General layer info


### Layer Namespace

Each layer has a reserved section in the `charms.layer.` Python package namespace,
which it can populate by including a `lib/charms/layer/<layer-name>.py` file or
by placing files under `lib/charms/layer/<layer-name>/`.  (If the layer name
includes hyphens, replace them with underscores.)  These can be helpers that the
layer uses internally, or it can expose classes or functions to be used by other
layers to interact with that layer.

For example, a layer named `foo` could include a `lib/charms/layer/foo.py` file
with some helper functions that other layers could access using:

```python
from charms.layer.foo import my_helper
```


### Layer Options

Any layer can define options in its `layer.yaml`.  Those options can then be set
by other layers to change the behavior of your layer.  The options are defined
using [jsonschema][], which is the same way that [action parameters][] are defined.

For example, the `foo` layer could include the following option definitons:

```yaml
includes: ['layer:basic']
defines:  # define some options for this layer (the layer "foo")
  enable-bar:  # define an "enable-bar" option for this layer
    description: If true, enable support for "bar".
    type: boolean
    default: false
```

A layer using `foo` could then set it:

```yaml
includes: ['layer:foo']
options:
  foo:  # setting options for the "foo" layer
    enable-bar: true  # set the "enable-bar" option to true
```

The `foo` layer can then use `charms.layer.options` to get the value for each
defined option. For example:

```python
from charms import layer

@when('flag')
def do_thing():
  # check the value of the "enable-bar" option for the "foo" layer
  if layer.options.get('foo', 'enable-bar'):
      hookenv.log("Bar is enabled")

  # or get all of the options for the "foo" layer as a dict
  foo_opts = layer.options.get('foo')
```

```eval_rst
.. note:: `charms.layer.options` is, itself, implemented as a layer named
   [`layer:options`][layer-options] and is automatically included when a layer
   includes [`layer:basic`][layer-basic]
```

You can also access layer options in other handlers, such as Bash, using
the command-line interface:

```bash
. charms.reactive.sh

@when 'flag'
function do_thing() {
    if layer_option foo enable-bar; then
        juju-log "Bar is enabled"
        juju-log "bar-value is: $(layer_option foo bar-value)"
    fi
}

reactive_handler_main
```

Note that options of type `boolean` will set the exit code, while other types
will be printed out.


[charm-helpers]: https://charm-helpers.readthedocs.io/
[charms.reactive]: https://charmsreactive.readthedocs.io/en/latest/
[interfaces.juju.solutions]: http://interfaces.juju.solutions/
[non-python]: https://charmsreactive.readthedocs.io/en/latest/bash-reactive.html
[external handler protocol]: https://charmsreactive.readthedocs.io/en/latest/charms.reactive.bus.html#charms.reactive.bus.ExternalHandler
[jsonschema]: http://json-schema.org/
[action parameters]: https://jaas.ai/docs/stable/developer-actions
[pypi charms.X]: https://pypi.python.org/pypi?%3Aaction=search&term=charms.&submit=search
[`requirements.txt`]: https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format
[layer-basic]: https://github.com/juju-solutions/layer-basic
[layer-options]: https://github.com/juju-solutions/layer-options

<!---
Hard-coding links to other charms.reactive docs is currently required.
https://github.com/rtfd/recommonmark/issues/8
-->
