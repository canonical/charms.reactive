# Introduction

This folder contains the design for the charms.reactive 2.0 reboot.

*Tip: Forget about hooks!*

# Index

[VISION.md](VISION.md) offers a short description of what charms.reactive is about and where we want to go.

# In general

Events trigger (set or unset) flags. Handlers react to flags and change them. Flags can have data attached to them.

That's it.

# Types of Events

### The world around us has changed! [external]

The external state outside of this unit has changed and we need to react to that.

Ex: `relation.changed` and `config.changed`.

### Lifecycle transition requested! [external]

The operator has requested that we bring the application into a new state of its lifecycle.

Ex: `install`, `start`, `stop`.

### Our internal state has changed! [internal]

The internal state of the unit has changed and we need to react to that.

Ex: A file changing (`file.changed.<xyz>`), landscape messing about on the system (removal of `apt.installed.xyz`), a flag being toggled or the data of a flag being changed (`config.changed` unsets `config.checked`).

<!-- ### Action requested!

The operator has requested an action that shouldn't significantly impact the state of the application.

Ex: `smoke-test`, `run-job`, `create-backup`, ... -->

# When do triggers and handlers run?

The flow of the framework is the following:

1. The reactive framework will run a handler when all its preconditions are met. A handler that has run is inactive. It will not run again until one of the flags it reacts to has changed. This change can be either the flag being toggled, or the flag data changing.

2. After each handler run, all internal events will be processed. The reactive framework will not remove flags itself. Only triggers can.

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

# Register Handlers
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
