# Background

Interface layers provide a valuable encapsulation of the protocol of
exchanging data over relations between charms that ensures all charms
using a given interface protocol know exactly what to expect and have
a documented API to use for interacting over the relation.

In previous implementations of the base classes for interface layers
attempts were made to model the flow of information over the relation
as a set of "conversations."  Unfortunately, this had too much mismatch
with how the underlying communication over the relations actually worked
and ended up being more difficult and confusing for interface layer authors.

The current incarnation, as described in this document, tries to stick
as close to the underlying Juju model as possible yet still provide
convenient methods for working with relations.

# Interface Layers

In Juju, relations consist of one or more endpoints on the local application
to which one or more remote applications can be connected (related).  A layer
which provides an interface implementation is a normal layer, but has to
conform to a certain set of requirements.  The layer must provide one or two
files with specific paths, containing classes that implement both the provides
and requires side of an interface, or the single peer interface implementation.

The files should be under the `reactive/relations/` directory, in a
sub-directory named after the interface name (with dashes changed to
underscores), and in files named one of `provides.py`, `requires.py`,
or `peers.py`.  Thus, the layer implementing the `apache-website` interface
would need to provide the following files:

  * `reactive/relations/apache_website/provides.py`
  * `reactive/relations/apache_website/requires.py`

The class in each of these files must be a subclass of
`charms.reactive.SimpleRelation`.

## Documenting Interface Layers

The classes provided by an interface layer are expected to use docstrings to
well document their API.  There is a `charm interface-doc` command that will
convert the docstrings into Markdown and inject them into the `README.md` file
between special comments of the form: &lt;!--interface-doc--&gt; and
&lt;!--/interface-doc--&gt;.  This way, all interface layers have consistent
and comprehensive documentation.

# Accessing Relation Instances

An instance of the appropriate interface layer class will be created and
added to the global reactive context variable, where it can be accessed
by the name of the relation (with dashes changed to underscores).  For example,
if a charm had the following in its `metadata.yaml`:

```yaml
provides:
  apache-website:
    interface: apache-website
requires:
  db:
    interface: mysql
peers:
  peers:
    interface: myapp
```

Then the following context attributes would be available:

```python
from charms.reactive import context

assert context.relations.apache_website
assert context.relations.db
assert context.relations.peers
```

Note that the `apache_website` instance would be of the class that was found in
the `reactive/relations/apache_website/provides.py` file, the `db` instance
would be from `reactive/relations/mysql/requires.py`, and the `peers` instance
would be from `reactive/relations/myapp/peers.py`, in their respective layers.

Also note that those instances would be available even if their relation is not
related to any remote application.

# The SimpleRelation API

The `SimpleRelation` base class will provide a couple of automatically managed
reactive flags, as well as providing collections for introspecting the state of
the relation, including related applications and units, relation data provided
by those units, and for associating reactive flags with particular related
applications or units and filtering related applications and units by those
flags.

## Managed Flags

The automatically managed flags are:

  * `relations.{relation_name}.joined`
  * `relations.{relation_name}.changed`

where the `{relation_name}` is replaced at runtime with the appropriate
relation name for that instance.  (The relation name for an instance can also
be accessed as `relation_instance.relation_name`.)

The `joined` flag will set as long as at least one remote unit is related via
the relation, and will be updated whenever the list of related units changes so
that any handler watching the flag will be re-invoked.

The `changed` flag will be set as long as at least one remote unit is
related and has set data on the relation, and it will be updated whenever
either a unit updates its relation data or if a related unit goes away.  The
interface can select only units whose relation data has changed using the
`with_flag` filter method described below and this flag.

## Application and Unit Collections

The interface layer can iterate over related applications and units using the
provided collections.  For example:

```python
class MyRelation(SimpleRelation):
    class flags:
        joined = 'relation.{relation_name}.joined'

    @when(flags.joined)
    def changed(self):
        for app in self.applications:
            for unit in app.units:
                print('Unit {} has data: {}'.format(unit.name, unit.data))
```

Applications and units can have flags associated with them.  Flags that are
added to an application are automatically added to all of that application's
units, even ones that join after the fact, and if a flag is added to at least
one of an application's units, that application will be considered to have that
flag.

You can filter the list of applications and units by flags.  For example:

```python
class MyRelation(SimpleRelation):
    class flags:
        changed = 'relation.{relation_name}.changed'
        ready = 'relation.{relation_name}.ready'

    @when(flags.changed)
    def changed(self):
        for app in self.applications:
            for unit in app.units.with_flag(self.flags.changed):
                host = unit.data.host
                print('unit {} host changed: {}'.format(unit.name, host))
                if host:
                    unit.add_flag(self.flags.ready)
                else:
                    unit.remove_flag(self.flags.ready)
                # or unit.toggle_flag(self.flags.ready, host)

        for app in self.applications.without_flag(self.flags.ready):
            print('Waiting on {}'.format(app.name))

    def get_hosts(self):
        for app in self.applications.with_flag(self.flags.ready):
            for unit in app.units.with_flag(self.flags.ready):
                yield unit.data.host
```

In the relatively common case that you don't expect or care about multiple
related applications, you can use the `self.all_units` view, which is roughly
analogous to `[u for a in self.applications for u in a.units]` except that it
also supports the filter and flag setting / removing methods.

It's important to note that each application in the collection actually
represents a relation, and so a given remote application might actually appear
in the collection multiple times if it is related more than once (for example,
if an application needed multiple databases).  However, the collection of units
and flags associated with the application or units will be kept separate.  You
can distinguish between the application instances by their `relation_id`
property.

## Relation Data

As shown above, each unit has a data attribute.  This behaves like a
read-only `defaultdict(None)` which allows the keys to be accessed as
attributes (with dashes converted to underscores).  The values are always
strings or `None`.

There is also a helper view for the relation data set by remote units, in case
you expect only the leader to be providing data or for the remote units to
agree on (some subset) of the data.  For example:

```python
class MySQLClient(SimpleRelation):
    class flags:
        changed = 'relation.{relation_name}.changed'
        ready = 'relation.{relation_name}.ready'

    @when(flags.changed)
    def changed(self):
        data = self.all_units.merged_data
        # we assume data.host to be the master
        if all([data.host, data.database, data.user, data.password]):
            self.add_flag(self.flags.ready)
```

To set relation data for the current unit, there is a `set_data` collection on
each application which behaves like the read-only data collection, but which
allows setting attributes or dictionary values.  For example:

```python
class MySQL(SimpleRelation):
    class flags:
        provided = 'relation.{relation_name}.provided'

    def requested_databases(self):
        return self.applications.without_flag(self.flags.provided)

    def provide_database(self, app, host, port, db, user, pass):
        app.set_data.host = host
        app.set_data.port = port
        app.set_data.database = db
        app.set_data.user = user
        app.set_data.password = pass
        app.add_flag(self.flags.provided)
```

It is often useful to have typed or structured data, which involves encoding
and decoding to something like JSON.  To make this easy, the data collections
support a JSON version which do automatic JSON encoding / decoding.

```python
class MyServicePeer(SimpleRelation):
    class flags:
        joined = 'relation.{relation_name}.joined'
        changed = 'relation.{relation_name}.changed'

    @when(flags.joined)
    def send_data(self):
        for app in self.applications:
            app.set_json_data.list = ['one', 'two']
            app.set_json_data.bool = True

    @when(flags.changed)
    def recv_data(self):
        for unit in self.all_units.with_flag(self.flags.changed):
            print('Peer {} list is {}'.format(unit, ', '.join(unit.json_data.list)))
            if unit.json_data.bool:
                print('Peer is bool')
```
