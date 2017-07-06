
Discovery and Dispatch of Reactive Handlers
-------------------------------------------

Reactive handlers are loaded from any file under the ``reactive`` directory,
as well as any interface layers you are using.  Handlers can be decorated blocks
in Python, or executable files following the :class:`~charms.reactive.bus.ExternalHandler`
protocol.  Handlers can be split amongst several files, which is particularly
useful for layers, as each layer can define its own file containing handlers
so as not to conflict with files from other layers.

Once all of the handlers are loaded, all :func:`@hook <charms.reactive.decorators.hook>`
handlers will be executed, in a non-determined order.  In general, only one layer
or relation stub should have a matching :func:`@hook <charms.reactive.decorators.hook>`
block for each hook, which should then set appropriate semantically meaningful
flags that the other layers can react to.  If there are multiple handlers that
match for a given hook, there is no guarantee which order they will execute in.
Hook handlers should live in the layer that is most appropriate for them.  The
base or runtime layer will probably handle the install and upgrade hooks, relation
stubs will handle all of the relation hooks, etc.

After all of the hook handlers have run, other handlers are dispatched based
on the flags set by the hook handlers and any flags from previous runs.
Various hook invocations can each set their appropriate flags, and the reactive
handlers will be triggered when all of the appropriate flags are set,
regardless of when and in which order they are each set.

All handlers are tested and matching handlers queued before invoking the
first handler.  Thus, flags set by a handler will not trigger new matching
handlers until after all of the current set of matching handlers are done.
This allows you to ensure some ordering of otherwise non-determined handler
invocation by chaining flags (e.g., handler_A sets flag_B, which triggers
handler_B which then sets flag_C, which triggers handler_C, and so on).

Note, however, that removing a flag causes the remaining set of matched handlers
to be re-tested.  This ensures that a handler is never invoked when the flag is
no longer active.
