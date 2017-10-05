# The case for triggers; the `apt` layer

The apt layer is such a great example of the strengths of the reactive framework; it's one of the most used layers, it does one job and it does it well, and the code is very clear, for the most part. Just look at the core of the apt layer code:

```python
@when('apt.needs_update')
def update():
    charms.apt.update()


@when('apt.queued_installs')
@when_not('apt.needs_update')
def install_queued():
    charms.apt.install_queued()


@when_not('apt.queued_installs')
def ensure_package_status():
    charms.apt.ensure_package_status()
```

Pretty logical flow, great use of states. You see how the apt layer works in 14! lines of code. Most importantly, the order in which these actions should run is dictated by states. Because of that, this code is very resilient to edge cases and this makes communication between layers very easy.

However, when you scroll down, you find a horrible hack at the end of the file.

```python
# Per https://github.com/juju-solutions/charms.reactive/issues/33,
# this module may be imported multiple times so ensure the
# initialization hook is only registered once. I have to piggy back
# onto the namespace of a module imported before reactive discovery
# to do this.
if not hasattr(reactive, '_apt_registered'):
    # We need to register this to run every hook, not just during install
    # and config-changed, to protect against race conditions. If we don't
    # do this, then the config in the hook environment may show updates
    # to running hooks well before the config-changed hook has been invoked
    # and the intialization provided an opertunity to be run.
    hookenv.atstart(hookenv.log, 'Initializing Apt Layer')
    hookenv.atstart(clear_removed_package_states)
    hookenv.atstart(configure_sources)
    hookenv.atstart(queue_layer_packages)
    hookenv.atstart(charms.apt.reset_application_version)
    reactive._apt_registered = True
```

What is this doing here? The first 14 lines cover all the basics. Why do we need to call `configure_sources` at the hook start? Why not do it this way?

```python
+ @when_not('apt.sources_configured')               
+ def sources():
+     configure_sources()
+     set_state('apt.sources_configured')


@when_all(
  'apt.needs_update',
+ 'apt.sources_configured')
def update():
    charms.apt.update()


@when('apt.queued_installs')
@when_not('apt.needs_update')
def install_queued():
    charms.apt.install_queued()


@when_not('apt.queued_installs')
def ensure_package_status():
    charms.apt.ensure_package_status()
```

Now we have the issue that if the `install_sources` config changes, the `apt.sources_configured` state becomes invalid **immediately**. We can create the following handler to do that.

```python
@when('config.changed.install_sources')
def unsource():
    remove_state('apt.sources_configured')
```

But we have no guarantee that this handler will run before any other handler. `@preflight` solves this issue, but it only solves it for this specific use-case where a changed config invalidates a state and it's very much tied to how hooks work. Triggers solve this issue more generally:


```python
+ @when_not('apt.sources_configured')               
+ def sources():
+     configure_sources()
+     set_state('apt.sources_configured')
++    charms.reactive.register_trigger(
++        event='config.changed.install_sources',
++        unset='apt.sources_configured')


@when_all(
  'apt.needs_update',
+ 'apt.sources_configured')
def update():
    charms.apt.update()


@when('apt.queued_installs')
@when_not('apt.needs_update')
def install_queued():
    charms.apt.install_queued()


@when_not('apt.queued_installs')
def ensure_package_status():
    charms.apt.ensure_package_status()
```

I don't mind changing the syntax and naming of this feature. This just makes it clear that we have a need for **invalidating flags/states IMMEDIATELY when something happens** and that with `preflight` we're taking on the symptoms instead of the root cause.

There are some reasons why I chose this specific syntax.

1. Any layer should be able to create a trigger for any flag, not just the layer that set the flag.
2. Triggers should also be able to set flags, not only invalidate them.

1 and 2 make it possible to solve the `config.changed` magic behavior.

3. Trigger should only be able to set/unset flags, nothing more, otherwise they will be used as handlers.

# Fix the delete mess

So we've seen why we need a way to invalidate flags/states immediately when something happens. Let's look at why we need a way to set flags/states immediately when something happens.

If we take another look at the atstart hack, we see that this also removes the `apt.removed.package` states at the start of each hook.

```python
# Warning! Magic happening here
hookenv.atstart(clear_removed_package_states)
```

We shouldn't remove states "magically" at the start or the end of the hook. Why do we do this?

1. When the `removed` state gets set, a bunch of handlers in upper layers *might* react to that state.
2. We want these handlers to run only one time.
3. A handler reacting to this state cannot remove the state because there might be another handler that also reacts to it, and we do not want to block that other handler.
4. So we don't remove the state in that handler, and we let the `apt` layer remove that state at the start of the next hook.

This has some obvious disadvantages. First of all, it **looks like magic** for users. Ask a random charmer how the `config.changed.x` states work, and you'll know what I mean.

Second of all, it creates non-obvious infinite loops. Fixing these loops still requires you to manually remove such states. Take the following example from a charm I recently wrote.

```python
@when(
    'ssl-termination-proxy.configured',
    'config.changed.credentials')
def configure_basic_auth():
    print('Credentials changed, re-triggering setup.')
    remove_state('ssl-termination-proxy.configured')
+    # To make sure we don't trigger an infinite loop.
+    remove_state('config.changed.credentials')
```

Without the last line, this would create an infinite loop in the `config-changed` hook. Now we have the issue that upper layers can't react to `config.changed.credentials` anymore because it will be removed by this layer. However, triggers fix that issue.




# Small improvements

There is room for some improvement towards readability. I prefer that all flags are set and removed in the handler itself instead of in the functions it calls. Something like this:

```python
@when('apt.needs_update')
def update():
   charms.apt.update()
+   remove_state('apt.needs_update')


@when('apt.queued_installs')
@when_not('apt.needs_update')
def install_queued():
   charms.apt.install_queued()
+   remove_state('apt.queued_installs')


@when_not('apt.queued_installs')
def ensure_package_status():
   charms.apt.ensure_package_status()
```

This makes the flow of the layer more explicit. Ofcourse that isn't always possible.
