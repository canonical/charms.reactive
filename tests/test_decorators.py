# Copyright 2014-2017 Canonical Limited.
#
# This file is part of charms.reactive.
#
# charms.reactive is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

import os
import mock
import shutil
import tempfile
import unittest

from charmhelpers.core import hookenv
from charmhelpers.core import unitdata
from charms import reactive


class TestReactiveDecorators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_dir = tempfile.mkdtemp()
        test_db = os.path.join(cls.test_db_dir, 'test-state.db')
        unitdata._KV = cls.kv = unitdata.Storage(test_db)
        cls._log = mock.patch('charmhelpers.core.hookenv.log')
        cls.log = cls._log.start()
        cls._charm_dir = mock.patch('charmhelpers.core.hookenv.charm_dir', lambda: 'charm_dir')
        cls._charm_dir.start()
        if not hasattr(cls, 'assertItemsEqual'):
            cls.assertItemsEqual = cls.assertCountEqual

    @classmethod
    def tearDownClass(cls):
        cls._log.stop()
        cls._charm_dir.stop()
        cls.kv.close()
        unitdata._KV = None
        shutil.rmtree(cls.test_db_dir)

    def tearDown(self):
        reactive.bus.Handler.clear()
        self.kv.cursor.execute('delete from kv')

    @mock.patch.object(hookenv, 'relation_type')
    @mock.patch.object(reactive.decorators, 'endpoint_from_name')
    @mock.patch.object(reactive.decorators, '_hook')
    def test_hook(self, _hook, from_name, relation_type):
        _hook.return_value = True
        from_name.return_value = 'RB.from_name'
        relation_type.return_value = 'rel_type'
        action = mock.Mock(name='action')

        @reactive.hook('{requires:mysql}-relation-{joined,changed}')
        def test_action(*args):
            action(*args)

        handler = reactive.bus.Handler.get(test_action)
        assert handler.test()
        handler.invoke()

        _hook.assert_called_once_with(('{requires:mysql}-relation-{joined,changed}',))
        from_name.assert_called_once_with('rel_type')
        action.assert_called_once_with('RB.from_name')

        delattr(handler, '_args_evaled')
        action.reset_mock()
        from_name.return_value = None
        handler.invoke()
        action.assert_called_once_with()

    @mock.patch.object(reactive.decorators, 'endpoint_from_flag')
    @mock.patch.object(reactive.decorators, '_action_id')
    @mock.patch.object(reactive.decorators, '_when_all')
    def test_when_all(self, _when_all, _action_id, from_flag):
        reactive.bus.Handler._CONSUMED_FLAGS.clear()
        _when_all.return_value = True
        _action_id.return_value = 'f:l:test_action'
        from_flag.side_effect = [None, 'rel', None]
        action = mock.Mock(name='action')

        @reactive.when_all('foo', 'bar', 'qux')
        def test_action(*args):
            action(*args)

        handler = reactive.bus.Handler.get(test_action)
        assert handler.test()
        handler.invoke()

        _when_all.assert_called_once_with(('foo', 'bar', 'qux'))
        self.assertEqual(from_flag.call_args_list, [
            mock.call('foo'),
            mock.call('bar'),
            mock.call('qux'),
        ])
        action.assert_called_once_with('rel')
        self.assertEqual(reactive.bus.Handler._CONSUMED_FLAGS, set(['foo', 'bar', 'qux']))

        action.reset_mock()
        assert handler.test()
        handler.invoke()
        action.assert_called_once_with('rel')

    @mock.patch.object(reactive.decorators, 'when_all')
    def test_when(self, when_all):
        @reactive.when('foo', 'bar', 'qux')
        def test_action(*args):
            pass
        when_all.assert_called_once_with('foo', 'bar', 'qux')

    @mock.patch.object(reactive.decorators, 'endpoint_from_flag')
    @mock.patch.object(reactive.decorators, '_action_id')
    @mock.patch.object(reactive.decorators, '_when_any')
    def test_when_any(self, _when_any, _action_id, from_flag):
        reactive.bus.Handler._CONSUMED_FLAGS.clear()
        _when_any.return_value = True
        _action_id.return_value = 'f:l:test_action'
        from_flag.side_effect = [None, 'rel', None]
        action = mock.Mock(name='action')

        @reactive.when_any('foo', 'bar', 'qux')
        def test_action(*args):
            action(*args)

        handler = reactive.bus.Handler.get(test_action)
        assert handler.test()
        handler.invoke()

        _when_any.assert_called_once_with(('foo', 'bar', 'qux'))
        assert not from_flag.called
        action.assert_called_once_with()
        self.assertEqual(reactive.bus.Handler._CONSUMED_FLAGS, set(['foo', 'bar', 'qux']))

    @mock.patch.object(reactive.decorators, 'endpoint_from_flag')
    @mock.patch.object(reactive.decorators, '_action_id')
    @mock.patch.object(reactive.decorators, '_when_none')
    def test_when_none(self, _when_none, _action_id, from_flag):
        reactive.bus.Handler._CONSUMED_FLAGS.clear()
        _when_none.return_value = True
        _action_id.return_value = 'f:l:test_action'
        from_flag.return_value = 'rel'
        action = mock.Mock(name='action')

        @reactive.when_none('foo', 'bar', 'qux')
        def test_action():
            action()

        handler = reactive.bus.Handler.get(test_action)
        assert handler.test()
        handler.invoke()

        _when_none.assert_called_once_with(('foo', 'bar', 'qux'))
        assert not from_flag.called
        action.assert_called_once_with()
        self.assertEqual(reactive.bus.Handler._CONSUMED_FLAGS, set(['foo', 'bar', 'qux']))

    @mock.patch.object(reactive.decorators, 'when_none')
    def test_when_not(self, when_none):
        @reactive.when_not('foo', 'bar', 'qux')
        def test_action(*args):
            pass
        when_none.assert_called_once_with('foo', 'bar', 'qux')

    @mock.patch.object(reactive.decorators, 'endpoint_from_flag')
    @mock.patch.object(reactive.decorators, '_action_id')
    @mock.patch.object(reactive.decorators, '_when_not_all')
    def test_when_not_all(self, _when_not_all, _action_id, from_flag):
        reactive.bus.Handler._CONSUMED_FLAGS.clear()
        _when_not_all.return_value = True
        _action_id.return_value = 'f:l:test_action'
        from_flag.return_value = 'rel'
        action = mock.Mock(name='action')

        @reactive.when_not_all('foo', 'bar', 'qux')
        def test_action():
            action()

        handler = reactive.bus.Handler.get(test_action)
        assert handler.test()
        handler.invoke()

        _when_not_all.assert_called_once_with(('foo', 'bar', 'qux'))
        assert not from_flag.called
        action.assert_called_once_with()
        self.assertEqual(reactive.bus.Handler._CONSUMED_FLAGS, set(['foo', 'bar', 'qux']))

    @mock.patch.object(reactive.decorators, 'any_file_changed')
    def test_when_file_changed(self, any_file_changed):
        any_file_changed.side_effect = [True, False]

        @reactive.decorators.when_file_changed('file1', 'file2')
        def test_action1():
            pass

        @reactive.decorators.when_file_changed('file3', 'file4', hash_type='sha256')
        def test_action2():
            pass

        handler1 = reactive.bus.Handler.get(test_action1)
        handler2 = reactive.bus.Handler.get(test_action2)
        assert handler1.test()
        assert not handler2.test()
        self.assertEqual(any_file_changed.call_args_list, [
            mock.call(('file1', 'file2')),
            mock.call(('file3', 'file4'), hash_type='sha256'),
        ])

    @mock.patch('charmhelpers.core.hookenv.log')
    def test_not_unless(self, log):
        action = mock.Mock()

        def log_msg(num):
            return log.call_args_list[num][0][0]

        @reactive.not_unless('foo', 'bar')
        def test():
            """Doc string."""
            action()

        self.assertEqual(test.__doc__, 'Doc string.')

        test()
        reactive.set_flag('foo')
        test()
        reactive.set_flag('bar')
        test()

        self.assertEqual(action.call_count, 3)
        assert log_msg(0).endswith('test called before flags: foo, bar'), log_msg(0)
        assert log_msg(1).endswith('test called before flag: bar'), log_msg(1)
        self.assertIn('tests/test_decorators.py:', reactive.bus._action_id(test))
        self.assertIn(':test', reactive.bus._action_id(test))
        self.assertIn('tests/test_decorators.py:', reactive.bus._short_action_id(test))
        self.assertIn(':test', reactive.bus._short_action_id(test))

    def test_only_once(self):
        calls = []

        @reactive.decorators.only_once
        def test():
            calls.append(len(calls) + 1)

        handler = reactive.bus.Handler.get(test)

        assert handler.test()
        handler.invoke()
        assert not handler.test()
        self.assertEquals(calls, [1])

    def test_only_once_parens(self):
        calls = []

        @reactive.decorators.only_once()
        def test():
            calls.append(len(calls) + 1)

        handler = reactive.bus.Handler.get(test)

        assert handler.test()
        handler.invoke()
        assert not handler.test()
        self.assertEquals(calls, [1])

    def test_multi(self):
        action1 = mock.Mock(name='action1')
        action2 = mock.Mock(name='action2')
        action3 = mock.Mock(name='action3')

        @reactive.when('foo')
        @reactive.when('bar')
        def test1():
            action1()

        @reactive.when('foo')
        @reactive.when_not('bar')
        def test2():
            action2()

        reactive.set_flag('foo')
        reactive.set_flag('bar')
        reactive.bus.dispatch()
        assert action1.called
        assert not action2.called

        action1.reset_mock()
        reactive.remove_state('bar')
        reactive.bus.dispatch()
        assert not action1.called
        assert action2.called

        @reactive.when('foo')
        def test3():
            action3()
            reactive.remove_state('bar')

        reactive.set_flag('bar')
        action2.reset_mock()
        reactive.bus.dispatch()
        assert action3.called
        assert action2.called  # should be called on second iteration

    @mock.patch.object(reactive.decorators, '_restricted_hook')
    def test_collect_metrics(self, _restricted_hook):
        _restricted_hook.return_value = True
        action = mock.Mock(name='action')

        @reactive.collect_metrics()
        def test_action(*args):
            action(*args)

        handler = reactive.bus.Handler.get(test_action)
        assert handler.test()
        handler.invoke()

        _restricted_hook.assert_called_once_with('collect-metrics')
        action.assert_called_once()

    @mock.patch.object(reactive.decorators, '_restricted_hook')
    def test_meter_status_changed(self, _restricted_hook):
        _restricted_hook.return_value = True
        action = mock.Mock(name='action')

        @reactive.meter_status_changed()
        def test_action(*args):
            action(*args)

        handler = reactive.bus.Handler.get(test_action)
        assert handler.test()
        handler.invoke()

        _restricted_hook.assert_called_once_with('meter-status-changed')
        action.assert_called_once()
