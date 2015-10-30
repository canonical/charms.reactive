import mock
from unittest import TestCase


class ReactiveTestCase(TestCase):
    @classmethod
    def _mock(cls, target, repl=mock.sentinel.DEFAULT):
        if not hasattr(cls, '_cleanups'):
            cls._cleanups = []
        patcher = mock.patch(target, repl)
        cls._cleanups.append(patcher.stop)
        return patcher.start()

    @classmethod
    def setUpClass(cls):
        cls._mock('charmhelpers.core.unitdata.kv').side_effect = NotImplementedError('Unmocked access to unitdata')
        cls._mock('charms.reactive.relations.Conversation.join').return_value = cls
        cls._mock('charms.reactive.relations.RelationBase.conversation').return_value = cls

    @classmethod
    def tearDownClass(cls):
        for cleanup in cls._cleanups:
            cleanup()

    @classmethod
    def set_state(cls, state):
        if not hasattr(cls, '_states'):
            cls._states = set()
        cls._states.add(state)

    @classmethod
    def remove_state(cls, state):
        if hasattr(cls, '_states'):
            cls._states.remove(state)

    def has_state(self, state):
        return state in getattr(self, '_states', set())

    def assert_state(self, state):
        self.assertIn(state, getattr(self, '_states', set()))

    def assert_not_state(self, state):
        self.assertNotIn(state, getattr(self, '_states', set()))

    @classmethod
    def set_local(cls, key=None, value=None, data=None, **kwdata):
        if data is None:
            data = {}
        if key is not None:
            data[key] = value
        data.update(kwdata)
        if not data:
            return
        if not hasattr(cls, '_local_data'):
            cls._local_data = {}
        cls._local_data.update(data)

    @classmethod
    def get_local(cls, key, default=None):
        return getattr(cls, '_local_data', {}).get(key, default)

    def assert_local(self, key, value):
        self.assert_local_eq(key, value)

    def assert_local_eq(self, key, value):
        self.assertEqual(self.get_local(key), value)

    def assert_local_ne(self, key, value):
        self.assertNotEqual(self.get_local(key), value)
