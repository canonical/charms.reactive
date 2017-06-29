Reactive Charms and Interface Layers
------------------------------------

Reactive charms work best as a part of layered charms, and the reactive pattern
enables the use of interface layers which encapsulate the communication protocol
over a Juju interface when two applications are related together.  By
encapsulating this protocol, it ensures that two applications that support the
same interface will always be able to speak to each other correctly.  It also
provides a well-defined and documented API for the charm author to use, without
having to get mired in the details of relation keys, data encoding, or what
order the communication has to proceed in.

Reactive enables interface layers to provide a set of flags that indicate
important points in the conversation so that the charm knows what information
to provide or what is available.  The interface layer can then provide the charm
with a documented set of methods to call to provide or access that data.
