import sys
import mock
import unittest

from charmhelpers.core import hookenv
from charms.reactive import relations


class DummyRelationSubclass(relations.RelationBase):
    auto_accessors = ['field-one', 'field-two']


class TestAutoAccessors(unittest.TestCase):
    def setUp(self):
        kv_p = mock.patch.object(relations.unitdata, 'kv')
        self.kv = kv_p.start()
        self.addCleanup(kv_p.stop)

    def test_accessor_doc(self):
        self.assertEqual(DummyRelationSubclass.field_one.__doc__, 'Get the field-one, if available, or None.')
        self.assertEqual(DummyRelationSubclass.field_one.__name__, 'field_one')
        self.assertEqual(DummyRelationSubclass.field_one.__module__, 'test_relations')

    def test_accessor(self):
        rel = DummyRelationSubclass('rel', [])
        rel.get_remote = mock.Mock(side_effect=['value1', 'value2'])
        self.assertEqual(rel.field_one(), 'value1')
        self.assertEqual(rel.field_two(), 'value2')
        self.assertEqual(rel.get_remote.call_args_list, [
            mock.call('field-one'),
            mock.call('field-two'),
        ])


class TestRelationBase(unittest.TestCase):
    def setUp(self):
        hookenv.cache = {}

    def test_find_subclass(self):
        self.assertIsNone(relations.RelationBase._find_subclass(unittest))
        self.assertIsNone(relations.RelationBase._find_subclass(relations))  # want strictly subclasses
        self.assertIs(
            relations.RelationBase._find_subclass(sys.modules[__name__]),
            DummyRelationSubclass)

    @mock.patch.object(relations.RelationBase, 'from_name')
    @mock.patch.object(relations.Conversation, 'load')
    @mock.patch.object(relations, 'get_state')
    def test_from_state(self, get_state, load, from_name):
        load.return_value = 'conv.load'
        get_state.side_effect = [{'relation': 'relname', 'conversations': ['conv']}, None]
        from_name.side_effect = lambda rn, c: 'from_name(%s, %s)' % (rn, c)
        self.assertEqual(relations.RelationBase.from_state('state'), 'from_name(relname, conv.load)')
        self.assertEqual(relations.RelationBase.from_state('no-state'), None)

    @mock.patch.object(relations.hookenv, 'relation_to_role_and_interface')
    @mock.patch.object(relations.Conversation, 'join')
    @mock.patch.object(relations.RelationBase, '_find_impl')
    def test_from_name(self, _find_impl, join, relation_to_role_and_interface):
        relation_to_role_and_interface.return_value = ('role', 'interface')
        r1 = mock.Mock(name='R1')
        _find_impl.side_effect = [None, r1, None]
        join.return_value = 'conv.join'

        self.assertIs(relations.RelationBase.from_name('none'), None)
        self.assertIs(relations.RelationBase.from_name('rel'), r1())

        # test cache
        self.assertEqual(_find_impl.call_count, 2)
        self.assertIs(relations.RelationBase.from_name('rel'), r1())
        self.assertEqual(_find_impl.call_count, 2)

        # test instantation
        relations.RelationBase._cache.clear()
        _find_impl.side_effect = [relations.RelationBase]
        res = relations.RelationBase.from_name('rel')
        self.assertIsInstance(res, relations.RelationBase)
        self.assertEqual(res._relation_name, 'rel')
        self.assertEqual(res.relation_name, 'rel')
        self.assertEqual(res._conversations, ['conv.join'])
        self.assertEqual(res.conversations(), ['conv.join'])

    @mock.patch.object(relations.hookenv, 'charm_dir')
    @mock.patch.object(relations.RelationBase, '_find_subclass')
    @mock.patch.object(relations, '_load_module')
    def test_find_impl(self, _load_module, find_subclass, charm_dir):
        charm_dir.return_value = 'charm_dir'
        _load_module.side_effect = ImportError
        self.assertIsNone(relations.RelationBase._find_impl('role', 'interface'))
        _load_module.assert_called_once_with('charm_dir/hooks/relations/interface/role.py')
        assert not find_subclass.called

        _load_module.reset_mock()
        _load_module.side_effect = None
        _load_module.return_value = m1 = mock.Mock(name='m1')
        find_subclass.return_value = r1 = mock.Mock(name='r1')
        self.assertIs(relations.RelationBase._find_impl('role', 'interface'), r1)
        _load_module.assert_called_once_with('charm_dir/hooks/relations/interface/role.py')
        find_subclass.assert_called_once_with(m1)

    @mock.patch.object(relations, 'hookenv')
    def test_conversation(self, hookenv):
        hookenv.remote_unit.return_value = 'remote_unit'
        hookenv.remote_service_name.return_value = 'remote_service_name'

        conv1 = mock.Mock(scope='remote_unit')
        conv2 = mock.Mock(scope='remote_service_name')
        conv3 = mock.Mock(scope='global')
        conv4 = mock.Mock(scope='explicit')
        rel = DummyRelationSubclass('relname', [conv1, conv2, conv3, conv4])

        self.assertIs(rel.conversation(), conv1)
        rel.scope = relations.scopes.SERVICE
        self.assertIs(rel.conversation(), conv2)
        rel.scope = relations.scopes.GLOBAL
        self.assertIs(rel.conversation(), conv3)
        self.assertIs(rel.conversation('explicit'), conv4)
        self.assertRaises(ValueError, rel.conversation, 'none')
        rel.scope = None
        self.assertRaises(ValueError, rel.conversation)

    def test_set_state(self):
        conv = mock.Mock(name='conv')
        rb = relations.RelationBase('relname', 'unit')
        rb.conversation = mock.Mock(return_value=conv)
        rb.set_state('state', 'scope')
        rb.conversation.assert_called_once_with('scope')
        conv.set_state.assert_called_once_with('state')

    def test_remove_state(self):
        conv = mock.Mock(name='conv')
        rb = relations.RelationBase('relname', 'unit')
        rb.conversation = mock.Mock(return_value=conv)
        rb.remove_state('state', 'scope')
        rb.conversation.assert_called_once_with('scope')
        conv.remove_state.assert_called_once_with('state')

    def test_set_remote(self):
        conv = mock.Mock(name='conv')
        rb = relations.RelationBase('relname', 'unit')
        rb.conversation = mock.Mock(return_value=conv)
        rb.set_remote('key', 'value', data='data', scope='scope', kwarg='value')
        rb.conversation.assert_called_once_with('scope')
        conv.set_remote.assert_called_once_with('key', 'value', 'data', kwarg='value')

    def test_get_remote(self):
        conv = mock.Mock(name='conv')
        rb = relations.RelationBase('relname', 'unit')
        rb.conversation = mock.Mock(return_value=conv)
        rb.get_remote('key', 'default', 'scope')
        rb.conversation.assert_called_once_with('scope')
        conv.get_remote.assert_called_once_with('key', 'default')

    def test_set_local(self):
        conv = mock.Mock(name='conv')
        rb = relations.RelationBase('relname', 'unit')
        rb.conversation = mock.Mock(return_value=conv)
        rb.set_local('key', 'value', data='data', scope='scope', kwarg='value')
        rb.conversation.assert_called_once_with('scope')
        conv.set_local.assert_called_once_with('key', 'value', 'data', kwarg='value')

    def test_get_local(self):
        conv = mock.Mock(name='conv')
        rb = relations.RelationBase('relname', 'unit')
        rb.conversation = mock.Mock(return_value=conv)
        rb.get_local('key', 'default', 'scope')
        rb.conversation.assert_called_once_with('scope')
        conv.get_local.assert_called_once_with('key', 'default')


class TestConversation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not hasattr(cls, 'assertItemsEqual'):
            cls.assertItemsEqual = cls.assertCountEqual

    @mock.patch.object(relations, 'hookenv')
    def test_init(self, hookenv):
        hookenv.relation_type.return_value = 'relation_type'
        hookenv.remote_unit.return_value = 'remote_unit'

        c1 = relations.Conversation()
        self.assertEqual(c1.relation_name, 'relation_type')
        self.assertEqual(c1.units, set(['remote_unit']))
        self.assertEqual(c1.scope, 'remote_unit')

        c2 = relations.Conversation('rel', ['unit'], 'scope')
        self.assertEqual(c2.relation_name, 'rel')
        self.assertEqual(c2.units, set(['unit']))
        self.assertEqual(c2.scope, 'scope')

    def test_key(self):
        c1 = relations.Conversation('rel', ['unit'], 'scope')
        self.assertEqual(c1.key, 'reactive.conversations.rel.scope')

    @mock.patch.object(relations.hookenv, 'remote_service_name')
    @mock.patch.object(relations.hookenv, 'relation_ids')
    def test_relation_ids(self, relation_ids, remote_service_name):
        relation_ids.return_value = ['rel:1', 'rel:2', 'rel:3']
        remote_service_name.side_effect = ['foo', 'bar', 'foo']
        c1 = relations.Conversation('rel', ['foo/1', 'qux/1', 'foo/2'], 'scope')
        self.assertEqual(c1.relation_ids, ['rel:1', 'rel:3'])
        self.assertEqual(remote_service_name.call_args_list, [
            mock.call('rel:1'),
            mock.call('rel:2'),
            mock.call('rel:3'),
        ])
        relation_ids.assert_called_once_with('rel')

        # test cache
        remote_service_name.reset_mock()
        remote_service_name.side_effect = ['foo', 'bar', 'foo']
        relation_ids.return_value = ['rel:4', 'rel:5', 'rel:6']
        self.assertEqual(c1.relation_ids, ['rel:1', 'rel:3'])
        assert not remote_service_name.called

        hookenv.cache.clear()
        self.assertEqual(c1.relation_ids, ['rel:4', 'rel:6'])
        self.assertEqual(remote_service_name.call_args_list, [
            mock.call('rel:4'),
            mock.call('rel:5'),
            mock.call('rel:6'),
        ])

    @mock.patch.object(relations, 'unitdata')
    @mock.patch.object(relations, 'hookenv')
    def test_join(self, hookenv, unitdata):
        hookenv.relation_type.return_value = 'relation_type'
        hookenv.remote_unit.return_value = 'service/0'
        hookenv.remote_service_name.return_value = 'service'
        unitdata.kv().get.side_effect = [
            {'scope': 'scope'},
            {
                'relation_name': 'relation_type',
                'units': {'service/1'},
                'scope': 'service',
            },
            {'scope': 'service/0'},
        ]
        conv = relations.Conversation.join('scope')
        self.assertEqual(conv.relation_name, 'relation_type')
        self.assertEqual(conv.units, {'service/0'})
        self.assertEqual(conv.scope, 'scope')
        unitdata.kv().get.assert_called_with('reactive.conversations.relation_type.scope', {'scope': 'scope'})
        unitdata.kv().set.assert_called_with('reactive.conversations.relation_type.scope', {
            'relation_name': 'relation_type',
            'units': ['service/0'],
            'scope': 'scope',
        })

        conv = relations.Conversation.join(relations.scopes.SERVICE)
        self.assertEqual(conv.relation_name, 'relation_type')
        self.assertEqual(conv.units, {'service/0', 'service/1'})
        self.assertEqual(conv.scope, 'service')
        unitdata.kv().get.assert_called_with('reactive.conversations.relation_type.service', {'scope': 'service'})
        self.assertEqual(unitdata.kv().set.call_args[0][0], 'reactive.conversations.relation_type.service')
        self.assertEqual(unitdata.kv().set.call_args[0][1]['relation_name'], 'relation_type')
        self.assertItemsEqual(unitdata.kv().set.call_args[0][1]['units'], ['service/0', 'service/1'])
        self.assertEqual(unitdata.kv().set.call_args[0][1]['scope'], 'service')

        conv = relations.Conversation.join(relations.scopes.UNIT)
        self.assertEqual(conv.relation_name, 'relation_type')
        self.assertEqual(conv.units, {'service/0'})
        self.assertEqual(conv.scope, 'service/0')
        unitdata.kv().get.assert_called_with('reactive.conversations.relation_type.service/0', {'scope': 'service/0'})
        unitdata.kv().set.assert_called_with('reactive.conversations.relation_type.service/0', {
            'relation_name': 'relation_type',
            'units': ['service/0'],
            'scope': 'service/0',
        })

    @mock.patch.object(relations, 'unitdata')
    @mock.patch.object(relations, 'hookenv')
    def test_depart(self, hookenv, unitdata):
        hookenv.remote_unit.return_value = 'service/0'
        conv = relations.Conversation('rel', ['service/0', 'service/1'], 'scope')
        conv.depart()
        self.assertEqual(conv.units, {'service/1'}, 'scope')
        unitdata.kv().set.assert_called_with(conv.key, {
            'relation_name': 'rel',
            'units': ['service/1'],
            'scope': 'scope',
        })
        assert not unitdata.kv().unset.called

        unitdata.kv().set.reset_mock()
        hookenv.remote_unit.return_value = 'service/1'
        conv.depart()
        assert not unitdata.kv().set.called
        unitdata.kv().unset.assert_called_with(conv.key)

    @mock.patch.object(relations, 'unitdata')
    def test_load(self, unitdata):
        unitdata.kv().get.side_effect = [
            {'relation_name': 'rel1', 'units': ['service/0'], 'scope': 'scope'},
            None,
            {'relation_name': 'rel2', 'units': ['service/1'], 'scope': 'service'},
        ]
        convs = relations.Conversation.load(['key1', 'key2', 'key3'])
        self.assertEqual(len(convs), 2)
        self.assertEqual(convs[0].relation_name, 'rel1')
        self.assertEqual(convs[0].units, {'service/0'})
        self.assertEqual(convs[0].scope, 'scope')
        self.assertEqual(convs[1].relation_name, 'rel2')
        self.assertEqual(convs[1].units, {'service/1'})
        self.assertEqual(convs[1].scope, 'service')
        self.assertEqual(unitdata.kv().get.call_args_list, [
            mock.call('key1'), mock.call('key2'), mock.call('key3'),
        ])

    @mock.patch.object(relations, 'set_state')
    @mock.patch.object(relations, 'get_state')
    def test_set_state(self, get_state, set_state):
        conv = relations.Conversation('rel', ['service/0', 'service/1'], 'scope')
        get_state.return_value = {'conversations': ['foo']}
        conv.set_state('{relation_name}.bar')
        set_state.assert_called_once_with('rel.bar', {'conversations': ['foo', 'reactive.conversations.rel.scope']})
        get_state.assert_called_once_with('rel.bar', {'relation': 'rel', 'conversations': []})

    @mock.patch.object(relations, 'remove_state')
    @mock.patch.object(relations, 'set_state')
    @mock.patch.object(relations, 'get_state')
    def test_remove_state(self, get_state, set_state, remove_state):
        conv = relations.Conversation('rel', ['service/0', 'service/1'], 'scope')
        get_state.side_effect = [
            None,
            {'conversations': ['foo', 'reactive.conversations.rel.scope']},
            {'conversations': ['reactive.conversations.rel.scope']},
        ]

        conv.remove_state('{relation_name}.bar')
        get_state.assert_called_once_with('rel.bar')
        assert not set_state.called
        assert not remove_state.called

        conv.remove_state('{relation_name}.bar')
        set_state.assert_called_once_with('rel.bar', {'conversations': ['foo']})
        assert not remove_state.called

        set_state.reset_mock()
        conv.remove_state('{relation_name}.bar')
        assert not set_state.called
        remove_state.assert_called_once_with('rel.bar')

    @mock.patch.object(relations.hookenv, 'relation_set')
    @mock.patch.object(relations.Conversation, 'relation_ids', ['rel:1', 'rel:2'])
    def test_set_remote(self, relation_set):
        conv = relations.Conversation('rel', ['service/0', 'service/1'], 'scope')

        conv.set_remote('foo', 'bar')
        self.assertEqual(relation_set.call_args_list, [
            mock.call('rel:1', {'foo': 'bar'}),
            mock.call('rel:2', {'foo': 'bar'}),
        ])
        relation_set.reset_mock()

        conv.set_remote(data={'foo': 'bar'})
        self.assertEqual(relation_set.call_args_list, [
            mock.call('rel:1', {'foo': 'bar'}),
            mock.call('rel:2', {'foo': 'bar'}),
        ])
        relation_set.reset_mock()

        conv.set_remote(foo='bar')
        self.assertEqual(relation_set.call_args_list, [
            mock.call('rel:1', {'foo': 'bar'}),
            mock.call('rel:2', {'foo': 'bar'}),
        ])
        relation_set.reset_mock()

        conv.set_remote('foo', 'bof', {'foo': 'bar'}, foo='qux')
        self.assertEqual(relation_set.call_args_list, [
            mock.call('rel:1', {'foo': 'qux'}),
            mock.call('rel:2', {'foo': 'qux'}),
        ])

        relation_set.reset_mock()
        conv.set_remote()
        assert not relation_set.called

    @mock.patch.object(relations.hookenv, 'relation_get')
    @mock.patch.object(relations.hookenv, 'related_units')
    @mock.patch.object(relations.Conversation, 'relation_ids', ['rel:1', 'rel:2'])
    def test_get_remote(self, related_units, relation_get):
        conv = relations.Conversation('rel', ['srv1/0', 'srv2/0', 'srv2/1'], 'scope')

        # set on at least one remote
        related_units.side_effect = [['srv1/0', 'srv1/1'], ['srv2/1']]
        relation_get.side_effect = [None, 'value']
        self.assertEqual(conv.get_remote('key', 'default'), 'value')
        self.assertEqual(related_units.call_args_list, [mock.call('rel:1'), mock.call('rel:2')])
        self.assertEqual(relation_get.call_args_list, [
            mock.call('key', 'srv1/0', 'rel:1'),
            mock.call('key', 'srv2/1', 'rel:2'),
        ])

        # not set on any remote
        related_units.side_effect = [[], ['srv2/0']]
        relation_get.side_effect = [None]
        self.assertEqual(conv.get_remote('key', 'default'), 'default')

        # no matching units
        related_units.side_effect = [['srv1/1'], []]
        relation_get.side_effect = AssertionError('relation_get should not be called')
        self.assertEqual(conv.get_remote('key', 'default'), 'default')

    @mock.patch.object(relations.unitdata, 'kv')
    def test_set_local(self, kv):
        conv = relations.Conversation('rel', ['srv1/0', 'srv2/0', 'srv2/1'], 'scope')
        conv.set_local('foo', 'bar')
        conv.set_local(data={'foo': 'bar'})
        conv.set_local(foo='bar')
        conv.set_local('foo', 'bof', data={'foo': 'bar'}, foo='qux')
        self.assertEqual(kv().update.call_args_list, [
            mock.call({'foo': 'bar'}, prefix='reactive.conversations.rel.scope.local-data.'),
            mock.call({'foo': 'bar'}, prefix='reactive.conversations.rel.scope.local-data.'),
            mock.call({'foo': 'bar'}, prefix='reactive.conversations.rel.scope.local-data.'),
            mock.call({'foo': 'qux'}, prefix='reactive.conversations.rel.scope.local-data.'),
        ])
        kv().update.reset_mock()
        conv.set_local()
        assert not kv().update.called

    @mock.patch.object(relations.unitdata, 'kv')
    def test_get_local(self, kv):
        conv = relations.Conversation('rel', ['srv1/0', 'srv2/0', 'srv2/1'], 'scope')
        conv.get_local('foo', 'default')
        kv().get.assert_called_once_with('reactive.conversations.rel.scope.local-data.foo', 'default')


class TestRelationCall(unittest.TestCase):
    def setUp(self):
        self.r1 = mock.Mock(name='r1')
        from_name_p = mock.patch.object(relations.RelationBase, 'from_name')
        self.from_name = from_name_p.start()
        self.addCleanup(from_name_p.stop)
        self.from_name.side_effect = lambda name: self.r1
        from_state_p = mock.patch.object(relations.RelationBase, 'from_state')
        self.from_state = from_state_p.start()
        self.addCleanup(from_state_p.stop)
        self.from_state.side_effect = lambda name: self.r1

    def test_no_impl(self):
        self.r1 = None
        self.assertRaises(ValueError, relations.relation_call, 'method', relation_name='rel')
        self.assertRaises(ValueError, relations.relation_call, 'method', state='state')
        self.assertRaises(ValueError, relations.relation_call, 'method')

    def test_call_name(self):
        self.r1.method.return_value = 'result'
        result = relations.relation_call('method', 'rel', None, 'arg1', 'arg2')
        self.assertEqual(result, 'result')
        self.r1.method.assert_called_once_with('arg1', 'arg2')
        self.from_name.assert_called_once_with('rel')

    def test_call_state(self):
        self.r1.method.return_value = 'result'
        result = relations.relation_call('method', None, 'state', 'arg1', 'arg2')
        self.assertEqual(result, 'result')
        self.r1.method.assert_called_once_with('arg1', 'arg2')
        self.from_state.assert_called_once_with('state')

    def test_call_conversations(self):
        self.r1.conversations.return_value = list(mock.Mock(scope=scope) for scope in ['s1', 's2'])
        result = relations.relation_call('conversations', 'rel')
        self.assertEqual(result, ['s1', 's2'])
