# What is charms.reactive and where do we want to go?

## Goals

 - **Layers** let you build on the work of other charmers.
 - **Interface Layers** define the protocol a protocol for charms to communicate.
 - **Flags** are used to communication between layers, and respond to certain conditions. Flags enable more complex orchestration logic than

Charms.reactive gives the community the tools to solve their problems. Challenges should be solved *with* the framework, not *in* the framework. This means that charms.reactive is as lean as possible.

**charms.reactive is not a config management tool.** It is a tool for coordinating config management.

 - charms.reactive is used to figure out what state you want to be in.
 - Config Management is used to get to that state.

The combination of charms.reactive + a config management tool like puppet is great. charms.reactive creates the puppetfile describing what state we want to be in and Puppet gets us to that state.

## Usability

It is important that using charms.reactive is easy. This translates into a number of usability goals.

 - The Juju lifecycle underneath charms.reactive is completely hidden from the user.
 - Clear and verbose is better than unclear and concise. It's better to have to do a bit more boilerplate than having stuff magically done for you.
 - No new concepts. Everything should be solvable using the `flag` and `layer` concepts.
