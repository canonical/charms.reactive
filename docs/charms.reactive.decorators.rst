charms.reactive.decorators
==========================

.. rubric:: Summary

These decorators turn a regular function into a reactive handler so that it will
be invoked if the conditions in the decorators are met. These decorators are
also called the preconditions of the handlers. If a handler has multiple
decorators, they will be ANDed together: the handler will only be invoked if
all of the individual decorators match.

Handlers are currently re-invoked for every hook execution, even if their
predicate flags have not changed. However, this may well change in the future,
and it is highly recommended that you not rely on this behavior. If you need to
ensure that a particular handler runs again, you should set or remove one of its
predicate flags.

Regular handlers should not accept any arguments. When a handler needs to use a
(relationship) :class:`~charms.reactive.endpoints.Endpoint`, it can access
the endpoint object via :func:`~charms.reactive.relations.endpoint_from_flag`.
The only exceptions to this are endpoint handlers, handlers that are instance
methods of :class:`~charms.reactive.endpoints.Endpoint`: they get the
endpoint object as the `self` argment.

For backwards compatibility, some decorators will pass endpoint instances if
the handler function specifies them as arguments.  However, explicit instance
access using ``endpoint_from_flag`` is recommended, because ensuring proper
argument order can be confusing: they are passed in bottom-up, left-to-right,
and no negative or ambiguous decorators, such as
:func:`~charms.reactive.decorators.when_not` or
:func:`~charms.reactive.decorators.when_any` will ever pass arguments. *Note
that a handler function that doesn't take arguments will never receive these
instances.*


.. automembersummary::
    :nosignatures:

    ~charms.reactive.decorators

.. rubric:: Reference

.. automodule:: charms.reactive.decorators
    :members:
    :undoc-members:
    :show-inheritance:
