# Background

Interface Layers codify the protocol that Charms use to exchange data over a relationship. A relationship connects two deployed Charms by connecting the `requires` endpoint of one Charm to the `provides` endpoint of the other Charm. This can only be done if both endpoints use the same interface. Both Charms then use this relation to send data to each other. **Both the `requires` and `provides` endpoint of an interface are encapsulated in the same Interface Layer to ensure that both sides understand the data that is being sent and received.**

Charms define relationship endpoints in their `metadata.yaml` using the `provides`, `requires` and `peers` keywords. In the following example, three endpoints are defined:

 - the endpoint `website` using the interface `apache-website`,
 - the endpoint `db` using the interface `mysql`,
 - and the endpoint `backup-db` using the interface `mysql`.

```yaml
provides:
  website:
    interface: apache-website
requires:
  db:
    interface: mysql
  backup-db:
    interface: mysql
```

This means that an operator can create a relationship between this Charm and a Charm implementing the requires endpoint of the `apache-website` or the provides endpoint of the `myqsl` interface.

## Interface Layers

Interface layers contain code for the `requires` and `provides` and `peer` side of a relationship in the `requires.py`, `provides.py` and `peers.py` files in the `reactive/interface/<interface_name>` directory (with dashes in the interface name changed to
underscores). Thus, the layer implementing the `apache-website` interface
would need to provide the following files:

  * `reactive/endpoint/apache_website/provides.py`
  * `reactive/endpoint/apache_website/requires.py`

Each file must contain a class that is a subclass of `charms.reactive.Endpoint`.

# Using Interface Layers

**Create the endpoints in `metadata.yaml`:**

```yaml
# ...
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

**Add the interface layer in `layer.yaml`:**

```yaml
# ...
includes:
  - layer:basic
  - interface:apache-website
  - interface:mysql
  - interface:myapp
```

**Respond to the flags of the interface layers in your handlers**

`charms.reactive` creates an instance of the endpoint class for each endpoint specified in `metadata.yaml`. You can find the instance at `charms.reactive.context.endpoint.<endpoint_name>` (with dashes in the interface name changed to underscores).

For example, the `metadata.yaml` from above will create the following instances:

```python
from charms.reactive import context.endpoint as endpoint

assert endpoint.apache_website
assert endpoint.db
assert endpoint.peers
# Yes, the instances exist!

@when('endpoint.db.changed')
def reconfigure_database():
    db_credentials = endpoint.db.get_credentials()
    #...
```

*Note that the `apache_website` instance would be of the class that was found in
the `reactive/endpoint/apache_website/provides.py` file, the `db` instance
would be from `reactive/endpoint/mysql/requires.py`, and the `peers` instance
would be from `reactive/endpoint/myapp/peers.py`, in their respective layers.*

*Also note that those instances would be available even if their relation is not
related to any remote application.*

# Writing Interface Layers

The `Endpoint` base class provides

 - a couple of automatically managed reactive flags that signal the state of the relationship,
 - collections of related applications and their units,
 - the relation data sent by those units,
 - collections to send relation data to those units,
 - methods to associates reactive flags with particular related applications or units,
 - and methods to filter the applications and units based on those flags.

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
related and has sent data over the endpoint. The `changed` flag and it will be
updated whenever either a unit changes that data or if a related unit goes
away.

## Relation and Unit Collections

The endpoint class can iterate over the relations and units using the provided
collections. One endpoint can have multiple relations. Each relation can have
multiple units corresponding to the units of the related application.

For example:

```python
class MyEndpoint(Endpoint):

    @when('endpoint.{relation_name}.joined')
    def changed(self):
        for rel in self.relations:
            for unit in rel.units:
                print('Unit {} sent data: {}'.format(unit.name, unit.receive))
```

Endpoint classes can use flags to signal the state of the relationship. Flags
set by Endpoint classes are identical to flags set in the handlers of normal
layers.

```python
class MyRelation(Endpoint):
    class flags:
        changed = 'endpoint.{relation_name}.changed'
        ready = 'endpoint.{relation_name}.ready'

    @when('endpoint.{relation_name}.changed')
    def changed(self):
        if self.get_hosts():
            add_flag('endpoint.{relation_name}.ready')
        else:
            remove_flag('endpoint.{relation_name}.ready')

    def get_hosts(self):
        hosts = []
        for rel in self.relations:
            for unit in rel.units:
                host = unit.receive['host']
                if host:
                    hosts.append('host')
                    print('unit {} hostname is: {}'.format(unit.name, host))
        return hosts
```

In the relatively common case that you don't expect or care about multiple
related applications, you can use the `self.all_units` view, which is roughly
analogous to `[u for r in self.relations for u in r.units]`.

## Sending and Receiving Relation Data

Units on each side of a relation communicate by sending and receiving relation
data in key-value pairs. Each `unit` has a `receive` attribute which behaves
like a read-only `defaultdict(None)` that contains the data you received from
that `unit`. The values are always non-empty strings or `None`.

```python
for rel in self.relations:
    for unit in rel.units:
        host = unit.receive['host']
        if host:
            add_flag('endpoint.{relation_name}.ready')
        else:
            remove_flag('endpoint.{relation_name}.ready')
```

There is also a helper view that merges the received data from all the units.
This is useful if you expect only the leader to be sending data or if you expect
the remote units to agree on (some subset) of the data.  For example:

```python
class MySQLClient(Endpoint):
    class flags:
        changed = 'endpoint.{relation_name}.changed'
        ready = 'endpoint.{relation_name}.ready'

    @when('endpoint.{relation_name}.changed')
    def changed(self):
        data = self.all_units.receive
        # we assume data['host'] to be the master
        if all([data['host'], data['database'],
                data['user'], data['password']]):
            self.add_flag('endpoint.{relation_name}.ready')
```

To send relation data to a unit of a remote application, you can use the
`send` attribute of an application. This is a dictionary that you use to send
key-value data. For example:

```python
class MySQL(Endpoint):
    class flags:
        provided = 'endpoint.{relation_name}.provided'

    def requested_databases(self):
        return self.relations.without_flag(self.flags.provided)

    def provide_database(self, app, host, port, db, user, pass):
        app.send['host'] = host
        app.send['port'] = port
        app.send['database'] = db
        app.send['user'] = user
        app.send['password'] = pass
        app.add_flag(self.flags.provided)
```

It is often useful to exchange typed or structured data. This involves encoding
and decoding data to JSON. To make this easy, the `send` and `receive`
collections have json counterparts: `send_json` and `receive_json`. These
collections do automatic encoding and decoding of serializable Python objects.

```python
class MyServicePeer(Endpoint):
    @when('endpoint.{relation_name}.joined')
    def send_data(self):
        for app in self.relations:
            app.send_json['my-list'] = ['one', 'two']
            app.send_json['my-bool'] = True

    @when('endpoint.{relation_name}.changed')
    def recv_data(self):
        for unit in self.all_units:
            print('The Peer {} sent us list {}.'.format(unit, ', '.join(unit.receive_json['my-list'])))
            if unit.receive_json['my-bool']:
                print('Peer says my-bool is True.')
```

## Documenting Interface Layers

The classes provided by an interface layer are expected to use docstrings to
document their API. There is a `charm interface-doc` command that converts
the docstrings into Markdown and inject them into the `README.md` file
between special comments of the form: &lt;!--interface-doc--&gt; and
&lt;!--/interface-doc--&gt;.  This way, all interface layers have consistent
and comprehensive documentation.
