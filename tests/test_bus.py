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
import re
import sys
import errno
import shutil
import tempfile
import unittest
import subprocess
from subprocess import Popen
from contextlib import contextmanager

import mock
from nose.plugins.attrib import attr

from charmhelpers.core import unitdata
from charms import reactive


class TestFlagWatch(unittest.TestCase):
    def setUp(self):
        self.key = reactive.bus.FlagWatch.key
        store_p = mock.patch.object(reactive.bus.FlagWatch, '_store')
        store = store_p.start()
        self.addCleanup(store_p.stop)
        self._data = {}
        store().get = self._data.get
        store().set = self._data.__setitem__
        store().unset = lambda k: self._data.pop(k, None)

    @property
    def data(self):
        return self._data.get(reactive.bus.FlagWatch.key, None)

    def test_reset(self):
        reactive.bus.FlagWatch.change('foo')
        reactive.bus.FlagWatch.reset()
        self.assertIsNone(self.data)

    def test_watch(self):
        reactive.bus.FlagWatch.reset()
        assert reactive.bus.FlagWatch.watch('foo', ['foos']), 'iter 0 (reset)'

        reactive.bus.FlagWatch.iteration(0)
        assert reactive.bus.FlagWatch.watch('foo', ['foos']), 'iter 0'

        reactive.bus.FlagWatch.iteration(1)
        assert not reactive.bus.FlagWatch.watch('foo', ['foos']), 'iter 1'

        reactive.bus.FlagWatch.change('foos')
        assert not reactive.bus.FlagWatch.watch('foo', ['foos']), 'uncommitted'

        reactive.bus.FlagWatch.commit()
        assert reactive.bus.FlagWatch.watch('foo', ['foos']), 'committed'

        reactive.bus.FlagWatch.change('bars')
        reactive.bus.FlagWatch.commit()
        assert not reactive.bus.FlagWatch.watch('foo', ['foos']), 'non-watched change'
        assert reactive.bus.FlagWatch.watch('bar', ['bars']), 'other watcher change'
        assert reactive.bus.FlagWatch.watch('foobar', ['foos', 'bars']), 'multi-watcher'

        reactive.bus.FlagWatch.commit()
        assert not reactive.bus.FlagWatch.watch('bar', ['bars']), 'already seen'
        assert not reactive.bus.FlagWatch.watch('foobar', ['foos', 'bars']), 'already seen multi'

        reactive.bus.FlagWatch.change('foos')
        reactive.bus.FlagWatch.change('bars')
        reactive.bus.FlagWatch.commit()
        assert reactive.bus.FlagWatch.watch('foo', ['foos']), 'multi-change, foo'
        assert reactive.bus.FlagWatch.watch('bar', ['bars']), 'multi-change, bar'
        assert reactive.bus.FlagWatch.watch('foobar', ['foos', 'bars']), 'multi-change, multi'
        assert not reactive.bus.FlagWatch.watch('qux', ['quxs']), 'multi-change, other'

        reactive.bus.FlagWatch.commit()
        assert not reactive.bus.FlagWatch.watch('foo', ['foos']), 'pre-reset'
        reactive.bus.FlagWatch.reset()
        assert reactive.bus.FlagWatch.watch('foo', ['foos']), 'post-reset'

    def test_change(self):
        reactive.bus.FlagWatch.change('foo')
        reactive.bus.FlagWatch.change('bar')
        self.assertEqual(self.data, {
            'iteration': 0,
            'pending': ['foo', 'bar'],
            'changes': [],
        })

    def test_commit(self):
        reactive.bus.FlagWatch.change('foo')
        reactive.bus.FlagWatch.change('bar')
        reactive.bus.FlagWatch.commit()
        self.assertEqual(self.data, {
            'iteration': 0,
            'pending': [],
            'changes': ['foo', 'bar'],
        })


class TestHandler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_dir = tempfile.mkdtemp()
        cls.test_db = os.path.join(cls.test_db_dir, 'test-state.db')
        unitdata._KV = cls.kv = unitdata.Storage(cls.test_db)
        cls._log = mock.patch('charmhelpers.core.hookenv.log')
        cls.log = cls._log.start()
        cls._log_opts = mock.patch.dict(reactive.bus.LOG_OPTS, register=True)
        cls._log_opts.start()
        cls._charm_dir = mock.patch('charmhelpers.core.hookenv.charm_dir', lambda: 'charm_dir')
        cls._charm_dir.start()
        if not hasattr(cls, 'assertItemsEqual'):
            cls.assertItemsEqual = cls.assertCountEqual

    @classmethod
    def tearDownClass(cls):
        cls._log_opts.stop()
        cls._log.stop()
        cls._charm_dir.stop()
        cls.kv.close()
        unitdata._KV = None
        shutil.rmtree(cls.test_db_dir)

    def tearDown(self):
        reactive.bus.Handler.clear()
        self.kv.cursor.execute('delete from kv')

    def test_get(self):
        def test_action():
            pass

        handler = reactive.bus.Handler.get(test_action)
        self.assertIsInstance(handler, reactive.bus.Handler)
        handler2 = reactive.bus.Handler.get(test_action)
        self.assertIs(handler2, handler)

    def test_add_call_test(self):
        action = mock.Mock(name='action')
        pred1 = mock.Mock(name='pred1', return_value=True)
        pred2 = mock.Mock(name='pred2', return_value=False)

        def test_action(*args):
            action(*args)

        handler = reactive.bus.Handler.get(test_action)

        handler.add_predicate(pred1)
        assert handler.test()
        handler.add_predicate(pred2)
        assert not handler.test()
        pred2.return_value = True
        assert handler.test()
        assert not action.called

        handler.register_flags(['state1', 'state2'])
        assert handler.test()
        reactive.bus.FlagWatch.iteration(1)
        assert not handler.test()
        reactive.bus.FlagWatch.change('state1')
        assert not handler.test()
        reactive.bus.FlagWatch.commit()
        assert handler.test()

    def test_args(self):
        def test_action():
            pass

        handler = reactive.bus.Handler.get(test_action)
        handler.add_args(['arg1', 'arg2'])
        handler.add_args(arg.upper() for arg in ['arg3', 'arg4'])
        arg5 = mock.MagicMock()
        arg5.__iter__.return_value = ['arg5']
        handler.add_args(arg5)
        assert not arg5.__iter__.called
        self.assertEqual(handler._get_args(), ['arg1', 'arg2', 'ARG3', 'ARG4', 'arg5'])
        assert arg5.__iter__.called

    def test_invoke(self):
        action = mock.Mock(name='action')

        def test_action(*args):
            action(*args)

        handler = reactive.bus.Handler.get(test_action)
        handler.add_args(['arg1', 'arg2'])
        handler.invoke()
        action.assert_called_once_with('arg1', 'arg2')


class TestExternalHandler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_dir = tempfile.mkdtemp()
        cls.test_db = os.path.join(cls.test_db_dir, 'test-state.db')
        unitdata._KV = cls.kv = unitdata.Storage(cls.test_db)
        cls._log = mock.patch('charmhelpers.core.hookenv.log')
        cls.log = cls._log.start()
        cls._log_opts = mock.patch.dict(reactive.bus.LOG_OPTS, register=True)
        cls._log_opts.start()
        cls._charm_dir = mock.patch('charmhelpers.core.hookenv.charm_dir', lambda: 'charm_dir')
        cls._charm_dir.start()
        if not hasattr(cls, 'assertItemsEqual'):
            cls.assertItemsEqual = cls.assertCountEqual

    @classmethod
    def tearDownClass(cls):
        cls._log_opts.stop()
        cls._log.stop()
        cls._charm_dir.stop()
        cls.kv.close()
        unitdata._KV = None
        shutil.rmtree(cls.test_db_dir)

    def tearDown(self):
        reactive.bus.Handler.clear()
        self.kv.cursor.execute('delete from kv')

    def test_register(self):
        handler1 = reactive.bus.ExternalHandler.register('filepath')
        handler2 = reactive.bus.ExternalHandler.register('filepath')
        handler3 = reactive.bus.ExternalHandler.register('filepath2')
        self.assertIs(handler1, handler2)
        self.assertIsNot(handler2, handler3)

    @mock.patch.object(os, 'environ', 'env')
    @mock.patch.object(reactive.bus.subprocess, 'Popen')
    def test_test(self, Popen):
        handler = reactive.bus.ExternalHandler('filepath')
        Popen.return_value.communicate.return_value = ('output', None)

        Popen.return_value.returncode = 0
        assert handler.test()

        Popen.return_value.returncode = 1
        assert not handler.test()
        Popen.assert_called_with(['filepath', '--test'], stdout=reactive.bus.subprocess.PIPE, env='env')

        e = Popen.side_effect = OSError()
        e.errno = errno.ENOEXEC
        self.assertRaises(reactive.bus.BrokenHandlerException, handler.test)
        e.errno = errno.ENOENT
        self.assertRaises(OSError, handler.test)

    @mock.patch.object(os, 'environ', 'env')
    @mock.patch.object(reactive.bus.subprocess, 'check_call')
    def test_invoke(self, check_call):
        handler = reactive.bus.ExternalHandler('filepath')
        handler._test_output = 'output'
        handler.invoke()
        check_call.assert_called_once_with(['filepath', '--invoke', 'output'], env='env')

        check_call.reset_mock()
        handler.invoke()
        check_call.assert_called_once_with(['filepath', '--invoke', 'output'], env='env')


class TestReactiveBus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_dir = tempfile.mkdtemp()
        cls.test_db = os.path.join(cls.test_db_dir, 'test-state.db')
        unitdata._KV = cls.kv = unitdata.Storage(cls.test_db)
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

    @mock.patch.object(reactive.bus.FlagWatch, 'change')
    def test_set_get_clear_flag(self, change):
        class states(reactive.flags.StateList):
            qux = reactive.flags.State('qux')

        reactive.set_flag('foo')
        reactive.set_flag('bar.ready', 'bar')
        reactive.set_flag(states.qux)
        self.assertEqual(reactive.flags.get_states(), {
            'foo': None,
            'bar.ready': 'bar',
            'qux': None,
        })
        reactive.clear_flag('foo')
        reactive.clear_flag('bar.ready')
        self.assertEqual(reactive.flags.get_states(), {
            'qux': None,
        })
        self.assertEqual(change.call_args_list, [
            mock.call('foo'),
            mock.call('bar.ready'),
            mock.call('qux'),
            mock.call('foo'),
            mock.call('bar.ready'),
        ])

    def test_dispatch(self):
        calls = []

        @reactive.when('foo')
        def foo():
            calls.append('foo')
            reactive.set_flag('bar')

        @reactive.when('bar')
        @reactive.only_once
        def bar():
            calls.append('bar')

        @reactive.when('foo', 'bar')
        def both():
            calls.append('both')
            reactive.set_flag('qux')

        @reactive.when('qux')
        def qux():
            calls.append('qux')

        @reactive.when('foo')
        def foo2():
            calls.append('foo2')

        @reactive.when('bar')
        def bar2():
            calls.append('bar2')

        reactive.bus.dispatch()
        self.assertEqual(calls, [])

        reactive.set_flag('foo')
        reactive.bus.dispatch()
        self.assertItemsEqual(calls[0:2], [
            'foo',
            'foo2',
        ])
        self.assertItemsEqual(calls[2:5], [
            'bar',
            'bar2',
            'both',
        ])
        self.assertItemsEqual(calls[5:], [
            'qux',
        ])

        # ensure that subsequent hooks will re-trigger all matching handlers (except only_once)
        calls = []
        reactive.bus.dispatch()
        self.assertItemsEqual(calls, [
            'foo',
            'both',
            'qux',
            'foo2',
            'bar2',
        ])

    @mock.patch.object(reactive.bus.Handler, 'get_handlers')
    def test_dispatch_remove(self, get_handlers):
        a = mock.Mock(name='a')
        a1 = lambda: a('h1') and reactive.clear_flag('foo')
        a2 = lambda: a('h2')
        a3 = lambda: a('h3')
        reactive.decorators.when('foo')(a1)
        reactive.decorators.when('foo')(a2)
        reactive.decorators.when('bar')(a3)
        h1 = reactive.bus.Handler.get(a1)
        h2 = reactive.bus.Handler.get(a2)
        h3 = reactive.bus.Handler.get(a3)

        reactive.set_flag('foo')
        reactive.set_flag('bar')
        get_handlers.return_value = [h1, h2, h3]
        reactive.bus.dispatch()
        self.assertEqual(a.call_args_list, [
            mock.call('h1'),
            mock.call('h3'),
        ])

        a.reset_mock()
        reactive.set_flag('foo')
        get_handlers.return_value = [h2, h1, h3]
        reactive.bus.dispatch()
        self.assertEqual(a.call_args_list, [
            mock.call('h2'),
            mock.call('h1'),
            mock.call('h3'),
        ])

    @mock.patch.object(reactive.bus.hookenv, 'hook_name')
    @mock.patch.object(reactive.bus.Handler, 'get_handlers')
    def test_dispatch_hook(self, get_handlers, hook_name):
        hook_name.return_value = 'fook'
        reactive.set_flag('foos')
        a = mock.Mock(name='a')
        a1 = lambda: a('h1')
        a2 = lambda: a('h2')
        reactive.decorators.when('foos')(a1)
        reactive.decorators.hook('fook')(a2)
        h1 = reactive.bus.Handler.get(a1)
        h2 = reactive.bus.Handler.get(a2)

        get_handlers.return_value = [h1, h2]
        reactive.bus.dispatch()
        self.assertEqual(a.call_args_list, [
            mock.call('h2'),
            mock.call('h1'),
        ])

        a.reset_mock()
        get_handlers.return_value = [h2, h1]
        reactive.bus.dispatch()
        self.assertEqual(a.call_args_list, [
            mock.call('h2'),
            mock.call('h1'),
        ])

    @mock.patch.dict('sys.modules')
    @mock.patch('charmhelpers.core.hookenv.charm_dir')
    def test_discover(self, charm_dir):
        test_dir = os.path.dirname(__file__)
        charm_dir.return_value = os.path.join(test_dir, 'data')

        self.assertEqual(len(reactive.bus.Handler.get_handlers()), 0)
        reactive.bus.discover()
        self.assertEqual(len(reactive.bus.Handler.get_handlers()), 19)

        # The path is extended so discovered modules can perform
        # absolute and relative imports as expected.
        self.assertListEqual(sys.path[-2:],
                             [charm_dir(), charm_dir() + '/hooks'])
        sys.path.pop()  # Repair sys.path
        sys.path.pop()

    @attr('slow')
    @mock.patch.dict('sys.modules')
    @mock.patch('charmhelpers.core.hookenv.relation_to_role_and_interface')
    @mock.patch('subprocess.check_call')
    @mock.patch('subprocess.Popen')
    @mock.patch('charmhelpers.core.hookenv.relation_type')
    @mock.patch('charmhelpers.core.hookenv.hook_name')
    @mock.patch('charmhelpers.core.hookenv.charm_dir')
    def test_full_stack(self, charm_dir, hook_name, relation_type, mPopen, mcheck_call, rtrai):
        test_dir = os.path.dirname(__file__)
        charm_dir.return_value = os.path.join(test_dir, 'data')
        hook_name.return_value = 'config-changed'
        relation_type.return_value = None

        mPopen.stdout = []
        mPopen.stderr = []

        def capture_output(proc):
            stdout, stderr = Popen.communicate(proc)
            mPopen.stdout.extend((stdout or b'').decode('utf-8').splitlines())
            mPopen.stderr.extend((stderr or b'').decode('utf-8').splitlines())
            return stdout, stderr

        def mock_Popen(*args, **kwargs):
            kwargs['stderr'] = subprocess.PIPE
            proc = Popen(*args, **kwargs)
            proc.communicate = lambda: capture_output(proc)
            return proc

        def mock_check_call(*args, **kwargs):
            proc = mock_Popen(*args, **kwargs)
            _, _ = proc.communicate()
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode,
                                                    args[0])

        mPopen.side_effect = mock_Popen
        mcheck_call.side_effect = mock_check_call
        with mock.patch.dict(os.environ, {
            'PATH': os.pathsep.join([
                os.path.dirname(sys.executable),  # for /usr/bin/env python
                ':%s' % os.path.join(test_dir, '..', 'bin'),  # for chlp
                os.environ['PATH'],
            ]),
            'PYTHONPATH': os.pathsep.join(sys.path),
            'UNIT_STATE_DB': self.test_db,
            'CHARM_DIR': charm_dir.return_value,
        }):
            self.assertEqual(len(reactive.bus.Handler.get_handlers()), 0)
            reactive.bus.discover()
            self.assertEqual(len(reactive.bus.Handler.get_handlers()), 19)

            reactive.set_flag('test')
            reactive.set_flag('to-remove')
            assert not reactive.helpers.any_flags_set('top-level', 'nested', 'test-rel.ready', 'relation', 'bash')
            reactive.bus.dispatch()
            assert reactive.helpers.all_flags_set('top-level')
            assert reactive.helpers.all_flags_set('nested')
            assert not reactive.helpers.any_flags_set('relation')
            assert not reactive.helpers.any_flags_set('test-rel.ready')
            assert not reactive.helpers.any_flags_set('top-level-repeat')
            assert reactive.helpers.all_flags_set('bash-when')
            assert not reactive.helpers.all_flags_set('bash-when-repeat')
            assert not reactive.helpers.all_flags_set('bash-when-neg')
            assert reactive.helpers.all_flags_set('bash-when-any')
            assert not reactive.helpers.all_flags_set('bash-when-any-repeat')
            assert reactive.helpers.all_flags_set('bash-when-not')
            assert not reactive.helpers.all_flags_set('bash-when-not-repeat')
            assert not reactive.helpers.all_flags_set('bash-when-not-neg')
            assert reactive.helpers.all_flags_set('bash-when-not-all')
            assert not reactive.helpers.all_flags_set('bash-when-not-all-repeat')
            assert reactive.helpers.all_flags_set('bash-only-once')
            assert not reactive.helpers.all_flags_set('bash-only-once-repeat')
            assert not reactive.helpers.all_flags_set('bash-hook')
            assert not reactive.helpers.all_flags_set('bash-hook-repeat')
            assert reactive.helpers.all_flags_set('bash-multi')
            assert not reactive.helpers.all_flags_set('bash-multi-repeat')
            assert not reactive.helpers.all_flags_set('bash-multi-neg')
            assert not reactive.helpers.all_flags_set('bash-multi-neg2')
            invoked = ['test_when_not_all', 'test_when_any', 'test_when',
                       'test_when_not', 'test_multi', 'test_only_once']
            invoked.sort()
            stdout_invoked = mPopen.stdout[0].split(',')
            stdout_invoked.sort()
            self.assertEqual(stdout_invoked, invoked)
            stderr_invoked = next(
                line for line in mPopen.stderr
                if line.startswith("Will invoke:")
            )[13:].split(',')
            stderr_invoked.sort()
            self.assertEqual(stderr_invoked, invoked)
            for handler in invoked:
                assert 'Invoking bash reactive handler: %s' % handler in mPopen.stderr
            assert '++ charms.reactive set_flag bash-when-not-all' in mPopen.stderr
            bash_debug = False
            debug_debug = False
            for line in mPopen.stderr:
                if re.match(r'\+ REACTIVE_HANDLERS\[\$func]=.*/bash.sh:', line):
                    bash_debug = True
                if re.match(r'\+ REACTIVE_HANDLERS\[\$func]=.*/debug.sh:', line):
                    debug_debug = True
            assert not bash_debug, 'CHARMS_REACTIVE_TRACE not enabled but has debug output'
            assert debug_debug, 'CHARMS_REACTIVE_TRACE enabled but missing debug output'

            hook_name.return_value = 'test-rel-relation-joined'
            relation_type.return_value = 'test-rel'
            rtrai.return_value = ('requires', 'test')
            self.assertIsNotNone(reactive.relations.relation_factory('test-rel'))
            self.assertIsNotNone(reactive.relations.relation_factory('test-rel').from_name('test'))
            with mock.patch.dict(os.environ, {'JUJU_HOOK_NAME': 'test-rel-relation-joined'}):
                reactive.bus.dispatch()
            assert reactive.helpers.all_flags_set('test-rel.ready')
            assert reactive.helpers.all_flags_set('relation')
            assert reactive.helpers.all_flags_set('test-remove-not')
            assert reactive.helpers.all_flags_set('bash-hook')
            assert not reactive.helpers.all_flags_set('bash-hook-repeat')
            print('\n'.join(mPopen.stderr))
            assert reactive.helpers.all_flags_set('bash-when-repeat')
            assert not reactive.helpers.all_flags_set('bash-only-once-repeat')

        # The path is extended so discovered modules can perform
        # absolute and relative imports as expected.
        self.assertListEqual(sys.path[-2:],
                             [charm_dir(), charm_dir() + '/hooks'])
        sys.path.pop()  # Repair sys.path
        sys.path.pop()

    @attr('slow')
    @mock.patch('charmhelpers.core.hookenv.log')
    def test_full_stack_with_tracing(self, log):
        self.addCleanup(reactive.trace.install_tracer, reactive.trace.NullTracer())
        tracer = mock.Mock(wraps=reactive.trace.LogTracer())
        reactive.trace.install_tracer(tracer)
        self.test_full_stack()
        log.assert_called()
        tracer.start_dispatch.assert_called()
        tracer.start_dispatch_phase.assert_any_call('hooks', mock.ANY)
        tracer.start_dispatch_phase.assert_any_call('other', mock.ANY)
        tracer.start_dispatch_iteration.assert_any_call(0, mock.ANY)

    @mock.patch.object(reactive.bus.importlib, 'import_module')
    def test_load_module_py3(self, import_module):
        import_module.side_effect = lambda x: x
        self.assertEqual(reactive.bus._load_module('/x/reactive',
                                                   '/x/reactive/file1.py'),
                         'reactive.file1')
        import_module.assert_called_once_with('reactive.file1')

        import_module.reset_mock()
        mod = reactive.bus._load_module('/x/hooks/relations',
                                        '/x/hooks/relations/iface/role.py')
        self.assertEqual(mod, 'relations.iface.role')
        import_module.assert_called_once_with('relations.iface.role')

        import_module.reset_mock()
        mod = reactive.bus._load_module('/x/hooks/reactive',
                                        '/x/hooks/reactive/sub/__init__.py')
        self.assertEqual(mod, 'reactive.sub')
        import_module.assert_called_once_with('reactive.sub')

    def test_load_module_really(self):
        # Look Ma, no mocks!
        here = os.path.dirname(__file__)
        root_path = os.path.join(here, 'data')

        # Path manipulation normally done by bus.discover()
        ext_path = [root_path, os.path.join(root_path, 'hooks')]
        with extended_sys_path(ext_path):
            top_mod = reactive.bus._load_module(os.path.join(root_path,
                                                             'reactive'),
                                                os.path.join(root_path,
                                                             'reactive',
                                                             'top_level.py'))
            sub_mod = reactive.bus._load_module(os.path.join(root_path,
                                                             'reactive'),
                                                os.path.join(root_path,
                                                             'reactive',
                                                             'nested',
                                                             'nested.py'))
            hyp_mod = reactive.bus._load_module(os.path.join(root_path,
                                                             'hooks',
                                                             'relations'),
                                                os.path.join(root_path,
                                                             'hooks',
                                                             'relations',
                                                             'hyphen-ated',
                                                             'peer.py'))

        self.assertEqual(top_mod.test_marker, 'top level')
        self.assertEqual(sub_mod.test_marker, 'nested')
        self.assertEqual(hyp_mod.test_marker, 'hyphenated-relation')

        self.assertIn('reactive.top_level', sys.modules)
        self.assertIn('reactive.nested.nested', sys.modules)
        self.assertIs(top_mod, sys.modules['reactive.top_level'])
        self.assertIs(sub_mod, sys.modules['reactive.nested.nested'])

    @mock.patch.object(reactive.bus.ExternalHandler, 'register')
    @mock.patch.object(reactive.bus, '_is_external_handler')
    @mock.patch.object(reactive.bus, '_load_module')
    def test_register_handlers_from_file(self, _load_module, _is_external_handler, register):
        reactive.bus._register_handlers_from_file('reactive',
                                                  'reactive/foo.py')
        _load_module.assert_called_once_with('reactive',
                                             'reactive/foo.py')
        _is_external_handler.return_value = True
        reactive.bus._register_handlers_from_file('reactive', 'reactive/foo')
        _is_external_handler.assert_called_once_with('reactive/foo')
        register.assert_called_once_with('reactive/foo')

        register.reset_mock()
        _is_external_handler.return_value = False
        reactive.bus._register_handlers_from_file('hooks/relations',
                                                  'hooks/relations/foo/README.md')
        assert not register.called


@contextmanager
def extended_sys_path(extras_list):
    extras_list = [p for p in extras_list if p not in sys.path]
    sys.path.extend(extras_list)
    try:
        yield
    finally:
        for p in extras_list:
            sys.path.remove(p)


if __name__ == '__main__':
    unittest.main()
