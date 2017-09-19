from charms.reactive import Endpoint, when


class TestAltRequires(Endpoint):
    invocations = []

    @when('relations.{relation_name}.joined')
    def handle_joined(self):
        self.invocations.append('joined: {}'.format(self.relation_name))

    @when('relations.{relation_name}.changed')
    def handle_changed(self):
        self.invocations.append('changed: {}'.format(self.relation_name))

    @when('relations.{relation_name}.changed.foo')
    def handle_changed_foo(self):
        self.invocations.append('changed.foo: {}'.format(self.relation_name))
