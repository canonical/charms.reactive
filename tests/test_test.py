from charms.reactive.test import ReactiveTestCase
from charms.reactive.relations import RelationBase
from charms.reactive.decorators import hook, when


class TestRelation(RelationBase):
    @hook('{interface:mysql}-relation-joined')
    def joined(self):
        self.set_state('{relation_name}.state')

    @when('rel.remove')
    def remove(self):
        self.remove_state('{relation_name}.state')

    def do_set(self):
        self.set_local('key', 'value')


class TestTest(ReactiveTestCase):
    def setUp(self):
        self.rel = TestRelation('rel')

    def test_state(self):
        self.rel.joined()
        self.assert_state('{relation_name}.state')
        self.rel.remove()
        self.assert_not_state('{relation_name}.state')

    def test_local(self):
        self.rel.do_set()
        self.assert_local('key', 'value')
