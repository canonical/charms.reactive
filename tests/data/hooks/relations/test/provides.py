from charms.reactive import RelationBase
from charms.reactive import scopes
from charms.reactive import when


class TestRelation(RelationBase):
    scope = scopes.UNIT

    @when('test-rel.ready')
    def test(self):
        self.set_local('call_count', self.get_local('call_count', 0) + 1)
        self.set_state('relation')
