# Introduction

This folder contains the design for the next evolution of charms.reactive: 2.0. We've learned a lot from using and breaking charms.reactive. We'll use this knowledge to tweak some of the core concepts to improve the experience of writing Charms.

*Tip: Forget about hooks!*

# Index

[VISION.md](VISION.md) provides a narrative of the evolution of charms.reactive and the principal aims of the project.

# In general

Events trigger (set or unset) flags. Handlers react to flags and change them. Flags can have data attached to them.

<!-- triggers are suggested here: https://github.com/juju-solutions/charms.reactive/issues/97 -->

That's it.

# Types of Events

### The world around us has changed! [external]

The external state outside of this unit has changed and we need to react to that.

Ex: `relation.changed` and `config.changed`.

### Lifecycle transition requested! [external]

The operator has requested that we bring the application into a new state of its lifecycle.

Ex: `install`, `start`, `stop`.

<!-- hooks are just one of the many types of events, decoupling the reactive bus from hooks as proposed here: https://github.com/juju-solutions/charms.reactive/issues/90 -->

### Our internal state has changed! [internal]

The internal state of the unit has changed and we need to react to that.

Ex: A file changing (`file.changed.<xyz>`), landscape messing about on the system (removal of `apt.installed.xyz`), a flag being toggled or the data of a flag being changed (`config.changed` unsets `config.checked`).

<!-- Actions is a tricky one. I'd wait a bit to include actions in the story until we're more certain of where we want to go.

### Action requested! [external]

The operator has requested an action that shouldn't significantly impact the state of the application.

Ex: `smoke-test`, `run-job`, `create-backup`, ... -->

# When do triggers and handlers run?

The flow of the framework is the following:

1. The reactive framework will run a handler when all its preconditions are met. A handler that has run is inactive. It will not run again until one of the flags it reacts to has changed. This change can be either the flag being toggled, or the flag data changing.

2. After each handler run, all internal events will be processed. The reactive framework will not remove flags itself. Only triggers and handlers can do that.

<!-- We should do step 2. recursively. This makes it possible for charmers to create deadlocks/ infinite loops. It would be good if the reactive framework could notice an infinite loop and crash. -->

<!-- Triggers or "Connected States" fix a number of issues:  -->
<!-- multiple handlers can watch the same file for changes by creating a trigger on `file.changed.xyz` that flags `myhandler.file.changed.xyz` https://github.com/juju-solutions/charms.reactive/issues/25 https://github.com/juju-solutions/charms.reactive/issues/44 -->
<!-- when_resource_changed is a trigger that flags `resource.changed.xyz` https://github.com/juju-solutions/charms.reactive/issues/87 -->


3. After all triggers have been processed, the reactive framework will run the next handler whose preconditions are met. (back to 1.)

The reactive framework goes into sleep mode when there isn't a handler to execute anymore at step 1. The reactive framework wakes up when an event happens.

# What is the difference between external and internal events?

Handlers run transactionally. Internal events are processed after a handler run. External events are processed when the reactive framework wakes up.

 - **All** internal events are processed after **every** handler run.
 - **Only one** external event is processed when the reactive framework wakes up. If there are still external events waiting to be processed at the moment the reactive framework goes to sleep, it will wake back up immediately and process the next external event.

# Show me the code!


```python
# Register triggers
charms.reactive.register_trigger(
  event='config.changed',
  unset='config.checked')

# Register Handlers See the reference for all the possible decorators
@when_all(
    "config.changed.my-json-value",
    "config.checked.my-json-value",
)
def set_config():
    # ...
    remove_flag('config.changed.my-json-value')
```

# Use Cases

## Config Validation

*Issue https://github.com/juju-solutions/charms.reactive/issues/98*

Charms need to be able to validate their config. You can put this config validation in layers. You can build on top of existing config validation layers to create more complex and application-specific config validation.

Simple example, config is checked in application layer.

```python
# Every time `config.changed` gets set, `config.checked` gets removed immediately; before
# running the next handler
reactive.register_trigger(event='config.changed', unset='config.checked')

@when("config.changed.my-json-value")
@when_not("config.checked.my-json-value")
def  check_config():
    my_json_value = hookenv.config()['my-json-value']
    if is_valid_json(my_json_value) :
         set_flag('config.checked.my-json-value')

@when_all(
    "config.changed.my-json-value",
    "config.checked.my-json-value",
)
def set_config():
    my_json_value = hookenv.config()['my-json-value']
    update_app_config(my_json_value)
    restart_app()
```

Complex example, a layer that checks the config values specified in layer options.

```python
# This layer will set the flag `config.checked.<key>` after checking if that config options is
# valid json. That flag will be immediately reset when that config option changes.

@when("config.changed")
@when_not("config.checked-json")
def  check_config():
    json_configs = layer.options('json-configs')
    for key in json_configs:
      json_value = hookenv.config()[key]
      if is_valid_json(json_value) :
           set_flag('config.checked-json.{}'.format(key))
           reactive.register_trigger(
              event='config.changed.{}'.format(key),
              unset='config.checked-json.{}'.format(key))
    reactive.register_trigger(
       event='config.changed',
       unset='config.checked-json')
```

# Reference

Multiple decorators on the same handler functions as an `AND`.

## `reactive.register`

Registers a trigger. This trigger will be checked after each handler.

- `event`: Trigger if this flag is set. *Note: after being triggered, it will become inactive until the event flag changes.*

<!-- Handlers and events both become inactive in the same way. This improves consistency. -->

Optional arguments:

- `set`: Set this flag when triggered.
- `unset`: Unset this flag when triggered.

## `reactive.decorators`

| decorator  	                 |   explanation                                                     |
|---	                         |---	                                                               |
| `when`, `when_all`           | Handler runs when all flags are set.                              |
| `when_any`                   | Handler runs when any of the flags are set.                       |
| `when_not`, `when_none`      | Handler runs when none of the flags are set.                      |
| `when_not_all`               | Handler runs when one or more of the flags are **not** set.       |


<!-- this proposal removes `hook`, `not_unless`, `only_once`, `when_file_changed` -->
<!-- fixes: https://github.com/juju-solutions/charms.reactive/issues/22 -->

# TODO

 - Figure out relations
 - Flesh out the API for flags that contain data
 - Figure out how to create new events (landscape is messing about)
 - Figure out what to do with actions
