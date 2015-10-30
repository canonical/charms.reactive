from charms.reactive import RelationBase
from charms.reactive import scopes
from charms.reactive import hook
from charms.reactive import when


class TestRelation(RelationBase):
    scope = scopes.GLOBAL

    @hook('{requires:test}-relation-joined')
    def joined(self):
        self.set_state('{relation_name}.ready')

    @when('test-rel.ready')
    def test(self):
        self.set_local('call_count', self.get_local('call_count', 0) + 1)
        self.set_state('relation')
