from charms.reactive import Endpoint, when


class TestAltRequires(Endpoint):
    invocations = []

    @when('endpoint.{endpoint_name}.joined')
    def handle_joined(self):
        self.invocations.append('joined: {}'.format(self.endpoint_name))

    @when('endpoint.{endpoint_name}.changed')
    def handle_changed(self):
        self.invocations.append('changed: {}'.format(self.endpoint_name))

    @when('endpoint.{endpoint_name}.changed.foo')
    def handle_changed_foo(self):
        self.invocations.append('changed.foo: {}'.format(self.endpoint_name))
