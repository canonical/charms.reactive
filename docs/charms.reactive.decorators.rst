charms.reactive.decorators
==========================

.. rubric:: Summary

These decorators are used to register a given function as a reactive handler
so that it will be invoked if the relevant combination of reactive flag
predicates are met.  If a given handler has multiple decorators, they should be
considered to be ANDed together; that is, the handler will only be invoked if
all of the individual decorators match.

Handlers are currently re-invoked for every hook execution, even if their
predicate flags have not changed.  However, this may well change in the future,
and it is highly recommended that you not rely on this behavior.  If you need to
ensure that a particular handler runs again, you should set or remove one of its
predicate flags.

Handlers should not accept any arguments (unless they are instance methods of
:class:`~charms.reactive.altrelations.Endpoint` classes), and can access the
:class:`~charms.reactive.altrelations.Endpoint` instances via the
:data:`~charms.reactive.helpers.context` (for older interface layers still
using :class:`~charms.reactive.relations.RelationBase` or if you're uncertain which is
used by an interface layer, you can also obtain an instance using
:func:`~charms.reactive.relations.relation_from_flag`).  For backwards compatibility,
some decorators can pass these instances in, but ensuring the proper argument
order can be confusing (they are passed in bottom-up, left-to-right, and no
negative or ambiguous decorators, such as :func:`~charms.reactive.decorators.when_not`
or :func:`~charms.reactive.decorators.when_any`) will
ever pass arguments), so the explicit instance access is reccomended.

.. automembersummary::
    :nosignatures:

    ~charms.reactive.decorators

.. rubric:: Reference

.. automodule:: charms.reactive.decorators
    :members:
    :undoc-members:
    :show-inheritance:
