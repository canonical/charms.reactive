# What is charms.reactive?

charms.reactive is a tool for **coordinating config management**. It is *not* a config management tool! A reactive agent figures out how an application needs to be configured. It can then use a config management tool to do the actual configuration. *As an example, a reactive agent might create a puppet manifest and then use `puppet apply` to apply that manifest to an application.*

Charms.reactive gives the community the tools to solve their problems. Challenges should be solved *with* the framework, not *in* the framework. This means that charms.reactive is as lean as possible.

# What problems does it solve?

 - **Figuring out state** of the application and its relations. The lifecycle approach of Juju wasn't flexible enough. Most Charms ended up having a single code file that was called by all hooks. This code file then checked a bunch of parameters to figure out what state the application and its relations were in, and then executed the right functions based on that state. Flags limit the need for manual checking of state.

 - We found out that a lot of Charms needed the same code, for example generating templates and installing packages. Sharing code using Python modules was brittle and inflexible. Layers are **a more flexible way to share code** and Flags provide a great way to coordinate operations between layers.

 - We had a lot of broken interfaces because each Charm implemented an interface slightly different. Interface Layers implement both sides of a relationship to **make sure both ends of the interface speak the same protocol**.

# Concepts

 - **Layers** are snippets of reusable ops code.
 - **Interface Layers** are layers that define the protocol for communication between Charms.
 - **Flags** are signals used for communication and coordination between layers and handlers.
 - **Triggers** change flags when certain events happen.
 - **Handlers** contain the actual ops code. Handlers react to a set of flags, execute code, and change flags. Flags are the only way to coordinate the order in which handlers must run.

# Usability

It is important that using charms.reactive is easy. This translates into a number of usability goals.

 - A charmer should be able to use charms.reactive correctly without knowing anything about hooks.
 - The behavior of the reactive framework should be explained using reactive concepts only. The charmer's understanding of the reactive framework shouldn't depend on his understanding of Juju's inner workings.
 - Clear and verbose is better than unclear and concise. It's better to have to do a bit more boilerplate than having stuff magically done for you.
 - No new concepts. Everything should be solvable using the `flag` and `layer` concepts.
