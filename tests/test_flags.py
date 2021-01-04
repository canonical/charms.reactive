import unittest

import mock

from charms.reactive import flags


class TestTriggers(unittest.TestCase):
    def setUp(self):
        kv_p = mock.patch('charmhelpers.core.unitdata.kv')
        kv = kv_p.start()
        self.addCleanup(kv_p.stop)
        kv.return_value = MockKV()

    def test_no_triggers(self):
        assert not flags.any_flags_set('foo', 'bar', 'qux')
        flags.set_flag('foo')
        assert not flags.any_flags_set('bar', 'qux')
        flags.clear_flag('foo')
        assert not flags.any_flags_set('foo', 'bar', 'qux')

    def test_when_set(self):
        flags.register_trigger(when='foo', set_flag='bar')
        flags.set_flag('foo')
        assert flags.is_flag_set('bar')
        flags.clear_flag('foo')
        assert flags.is_flag_set('bar')

    def test_when_clear(self):
        flags.register_trigger(when='foo', clear_flag='qux')
        flags.set_flag('qux')
        flags.set_flag('foo')
        assert not flags.is_flag_set('qux')

    def test_when_not_set_clear(self):
        flags.register_trigger(when_not='foo',
                               set_flag='bar',
                               clear_flag='qux')
        flags.set_flag('noop')
        flags.clear_flag('noop')
        assert not flags.is_flag_set('bar')

        flags.set_flag('foo')
        flags.set_flag('qux')
        assert not flags.is_flag_set('bar')
        flags.clear_flag('foo')
        assert flags.is_flag_set('bar')
        assert not flags.is_flag_set('qux')

    def test_callbacks(self):
        a = mock.Mock()
        b = mock.Mock()
        c = mock.Mock()
        flags.register_trigger(when='a', callback=a)
        flags.register_trigger(when_not='b', callback=b)
        flags.set_flag('a')
        assert a.call_count == 1
        assert b.call_count == 0
        assert c.call_count == 0
        flags.clear_flag('a')
        assert a.call_count == 1
        assert b.call_count == 0
        assert c.call_count == 0
        flags.set_flag('b')
        assert a.call_count == 1
        assert b.call_count == 0
        assert c.call_count == 0
        flags.clear_flag('b')
        assert a.call_count == 1
        assert b.call_count == 1
        assert c.call_count == 0
        flags.set_flag('c')
        assert a.call_count == 1
        assert b.call_count == 1
        assert c.call_count == 0
        flags.clear_flag('c')
        assert a.call_count == 1
        assert b.call_count == 1
        assert c.call_count == 0

    def test_get_unset_flags(self):
        self.assertEqual(flags.get_flags(), [])
        flags.set_flag('foo')
        self.assertEqual(flags.get_flags(), ['foo'])
        self.assertEqual(flags.get_unset_flags('foo', 'bar'), ['bar'])


class MockKV:
    def __init__(self):
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def getrange(self, prefix, strip=False):
        results = {}
        for key, value in self.data.items():
            if key.startswith(prefix):
                if strip:
                    key = key[len(prefix):]
                results[key] = value
        return results

    def set(self, key, value):
        self.data[key] = value

    def update(self, data, prefix=''):
        for key, value in data.items():
            self.set(prefix + key, value)

    def unset(self, key):
        self.data.pop(key, None)


if __name__ == '__main__':
    unittest.main()
