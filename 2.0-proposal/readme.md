# Introduction

This folder contains the design for the next evolution of charms.reactive: 2.0. We've learned a lot from using and breaking charms.reactive. We'll use this knowledge to tweak some of the core concepts to improve the experience of writing Charms.

*Tip: Forget about hooks!*

# Index

[VISION.md](VISION.md) provides a narrative of the evolution of charms.reactive and the principal aims of the project.

# In general

In a nutshell: events trigger (set or unset) flags. Handlers react to flags and change them. Flags can have objects attached to them.

# Handlers

**Handlers** contain the actual ops code. Handlers react to a set of flags, execute code, and change flags. Flags are the only way to coordinate the order in which handlers must run.

# Triggers

The order in which handlers run is only determined by the flags. This provides a very flexible way for coordinating the order in which handlers run across layers. This also means that these flags have to be correct as much as possible or bad stuff might happen.

Certain events can invalidate flags. The example is that when the config of a charm changes, the `config.checked` flag needs to be invalidated immediately, otherwise we risk handlers using the unchecked config.

That is what triggers are for. They allow charmers to connect to certain events and flags. Triggers run before each handler so that the flags are always up-to-date. The order of handlers is still coordinated by the flags. Triggers allows charmers to have these flags represent the truth more.


<!-- Triggers or "Connected States" fix a number of issues:  -->
<!-- multiple handlers can watch the same file for changes by creating a trigger on `file.changed.xyz` that flags `myhandler.file.changed.xyz` https://github.com/juju-solutions/charms.reactive/issues/25 https://github.com/juju-solutions/charms.reactive/issues/44 -->
<!-- when_resource_changed is a trigger that flags `resource.changed.xyz` https://github.com/juju-solutions/charms.reactive/issues/87 -->


### External Events

External events can indicate two things:

1. The external state has changed.
2. An operator has requested a certain action.

The reactive agent translates all hooks into external events. Either the external state has changed wich will trigger flags like `config.changed` and `httpclient.changed` or the operator has requested a certain action which will be translated into flags like `upgrade` and `stop`.

Initially, hooks will be the only sources of external events, although there are plans to support more external events in the future. See https://github.com/juju-solutions/charms.reactive/issues/90

### Internal Events

Internal events can be changes in flags and changes in the internal state of the unit.

A file changing (`file.changed.<xyz>`), landscape messing about on the system (removal of `apt.installed.xyz`), a flag being toggled or the data of a flag being changed (`config.changed` unsets `config.checked`).

### Custom Events

TODO

Events is a generic concept that substitutes the multitude of decorators such as `when_file_changed`.

Layer devs will be able to use this to create their own when_file_changed-like flags. Layer devs continue making smarter layers without needing to add additional stuff to reactive.

# When do handlers and triggers run?

The Reactive Agent has two modes: `idle` and `executing`. An idle agent waits for events to happen. When an event happens, the agent wakes up, processes the event by changing the linked flags, and runs handlers to react to those flags. You can see the agent state in the "Agent" field of the `juju status` output.

1. Wake up and **process process one external event.**
  - Set or change the flags corresponding to that external event.
  - Remove the external event from the external event queue.


2. **Process all internal events and triggers.**
  - Process all internal events and triggers recursively until no events are left.
  - Mark all inactive handlers whose flags have changed as active.


3. **Run one handler.**
  - Run a randomly selected active handler whose preconditions are met. If no handler is found, go into idle mode.
  - Mark that handler as inactive.
  <!-- The `inactive` bit has the effect that a handler will not rerun if its flags don't change. The handler doesn't need to rerun because "it has already reacted to the flags". -->


4. Back to 2.

All external events will be put on a FIFO queue. Each time the agent wakes up, it will process the next element of that queue. If the agent goes into idle mode while there are still external events on the queue, it will wake back up immediately to process the next event on the queue.

# What is the difference between external and internal events?

Handlers run transactionally. Internal events are processed after a handler run. External events are processed when the reactive agent wakes up.

 - **All** internal events are processed after **every** handler run.
 - **Only one** external event is processed when the reactive agent wakes up. If there are still external events waiting to be processed at the moment the reactive agent goes to sleep, it will wake back up immediately and process the next external event.

# FAQ

 - **What do we do with infinite loops?** A: The reactive agent can't prevent infinite loops but it can notice them and crash. Reactive 1.0 crashes after 100 iterations, this might be something we want to keep.

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

## I want to react to a flag regardless of whether another handler has removed the flag in the meantime.

TODO

## I want to react to `apt.installed.x` but I don't know what `x` will be until runtime.

TODO

## My handler needs to be notified when Landscape removes a package.

TODO

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
