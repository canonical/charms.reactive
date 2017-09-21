from charms.reactive import Endpoint, when


class TestAltProvides(Endpoint):
    invocations = []

    @when('endpoint.{relation_name}.joined')
    def handle_joined(self):
        self.invocations.append('joined: {}'.format(self.relation_name))

    @when('endpoint.{relation_name}.changed')
    def handle_changed(self):
        self.invocations.append('changed: {}'.format(self.relation_name))

    @when('endpoint.{relation_name}.changed.foo')
    def handle_changed_foo(self):
        self.invocations.append('changed.foo: {}'.format(self.relation_name))
