import unittest

import mock

from charms.reactive import flags


class TestTriggers(unittest.TestCase):
    @mock.patch('charmhelpers.core.unitdata.kv')
    def test_triggers(self, kv):
        kv.return_value = MockKV()

        assert not flags.any_flags_set('foo', 'bar', 'qux')
        flags.set_flag('foo')
        assert not flags.any_flags_set('bar', 'qux')
        flags.clear_flag('foo')
        assert not flags.any_flags_set('foo', 'bar', 'qux')

        flags.register_trigger(when='foo', set_flag='bar')
        flags.set_flag('foo')
        assert flags.is_flag_set('bar')
        flags.clear_flag('foo')
        assert flags.is_flag_set('bar')
        flags.clear_flag('bar')

        flags.register_trigger(when='foo', clear_flag='qux')
        flags.set_flag('qux')
        flags.set_flag('foo')
        assert not flags.is_flag_set('qux')


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
