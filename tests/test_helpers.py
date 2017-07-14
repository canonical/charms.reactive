# Copyright 2014-2015 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
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

import re
import os
import mock
import shutil
import tempfile
import unittest

from charmhelpers.core import unitdata
from charms import reactive


class TestReactiveHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_dir = tempfile.mkdtemp()
        test_db = os.path.join(cls.test_db_dir, 'test-state.db')
        unitdata._KV = cls.kv = unitdata.Storage(test_db)
        if not hasattr(cls, 'assertItemsEqual'):
            cls.assertItemsEqual = cls.assertCountEqual

    @classmethod
    def tearDownClass(cls):
        cls.kv.close()
        unitdata._KV = None
        shutil.rmtree(cls.test_db_dir)

    def tearDown(self):
        self.kv.cursor.execute('delete from kv')

    def test_toggle_state(self):
        reactive.toggle_state('foo', True)
        reactive.toggle_state('foo', True)
        reactive.toggle_state('bar', False)
        reactive.toggle_state('bar', False)
        assert reactive.is_state('foo')
        assert not reactive.is_state('bar')

    def test_is_state(self):
        assert not reactive.is_state('foo')
        reactive.set_flag('foo')
        assert reactive.is_state('foo')

    def test_all_flags(self):
        reactive.set_flag('foo')
        reactive.set_flag('bar')
        assert reactive.all_flags_set('foo')
        assert reactive.all_flags_set('bar')
        assert reactive.all_flags_set('foo', 'bar')
        assert not reactive.all_flags_set('foo', 'bar', 'qux')
        assert not reactive.all_flags_set('foo', 'qux')
        assert not reactive.all_flags_set('bar', 'qux')
        assert not reactive.all_flags_set('qux')

    def test_any_flags(self):
        reactive.set_flag('foo')
        reactive.set_flag('bar')
        assert reactive.any_flags_set('foo')
        assert reactive.any_flags_set('bar')
        assert reactive.any_flags_set('foo', 'bar')
        assert reactive.any_flags_set('foo', 'bar', 'qux')
        assert reactive.any_flags_set('foo', 'qux')
        assert reactive.any_flags_set('bar', 'qux')
        assert not reactive.any_flags_set('qux')

    def test_expand_replacements(self):
        er = reactive.helpers._expand_replacements
        pat = re.compile(r'{([^}]+)}')
        self.assertItemsEqual(er(pat, lambda v: [v], ['A']), ['A'])
        self.assertItemsEqual(er(pat, lambda v: [v], ['{A}']), ['A'])
        self.assertItemsEqual(er(pat, lambda v: v.split(','), ['{A,B}']), ['A', 'B'])
        self.assertItemsEqual(er(pat, lambda v: v.split(','), ['{A,B}', '{C,D}']), ['A', 'B', 'C', 'D'])
        self.assertItemsEqual(er(pat, lambda v: v.split(','), ['{A,B}{C,D}']), ['AC', 'BC', 'AD', 'BD'])
        self.assertItemsEqual(er(pat, lambda v: v.split(','), ['{A,B}{A,B}']), ['AA', 'BA', 'AB', 'BB'])

    @mock.patch('charmhelpers.core.hookenv.metadata')
    @mock.patch('charmhelpers.core.hookenv.hook_name')
    def test_any_hook(self, hook_name, metadata):
        hook_name.return_value = 'config-changed'
        metadata.return_value = {}
        assert not reactive.helpers.any_hook('foo', 'bar')
        assert reactive.helpers.any_hook('foo', 'config-changed')
        assert reactive.helpers.any_hook('foo', 'config-{set,changed}')
        assert reactive.helpers.any_hook('foo', 'config-{changed,set}')
        assert reactive.helpers.any_hook('foo', '{config,option}-{changed,set}')

        metadata.return_value = {
            'requires': {
                'db1': {'interface': 'mysql'},
                'db2': {'interface': 'postgres'},
            },
            'provides': {
                'db3': {'interface': 'mysql'},
            },
        }
        hook_name.return_value = 'db1-relation-changed'
        assert not reactive.helpers.any_hook('{requires:http}-relation-changed')
        assert not reactive.helpers.any_hook('{requires:postgres}-relation-changed')
        assert reactive.helpers.any_hook('{requires:mysql}-relation-changed')
        hook_name.return_value = 'db3-relation-changed'
        assert not reactive.helpers.any_hook('{requires:mysql}-relation-changed')
        assert reactive.helpers.any_hook('{provides:mysql}-relation-changed')
        assert reactive.helpers.any_hook('{provides:mysql}-relation-{joined,changed}')

    @mock.patch('charmhelpers.core.host.file_hash')
    def test_any_file_changed(self, file_hash):
        self.kv.update({
            'file1': 'hash1',
            'file2': 'hash2',
            'file3': 'hash3',
        }, prefix='reactive.files_changed.')
        file_hash.side_effect = [
            # file2 and file3 change
            'hash1',
            'hash1', 'changed1',
            'changed2',

            # no changes
            'hash1',
            'hash1', 'changed1',
            'changed2',
        ]
        afc = reactive.helpers.any_file_changed
        assert not afc(['file1'])
        assert afc(['file1', 'file2'])
        assert afc(['file3'], hash_type='sha256')

        assert not afc(['file1'])
        assert not afc(['file1', 'file2'])
        assert not afc(['file3'])

        self.assertEqual(file_hash.call_args_list, [
            mock.call('file1', hash_type='md5'),
            mock.call('file1', hash_type='md5'),
            mock.call('file2', hash_type='md5'),
            mock.call('file3', hash_type='sha256'),
            mock.call('file1', hash_type='md5'),
            mock.call('file1', hash_type='md5'),
            mock.call('file2', hash_type='md5'),
            mock.call('file3', hash_type='md5'),
        ])

    @mock.patch('charmhelpers.core.host.file_hash')
    def test_any_file_changed_argtypes(self, file_hash):
        file_hash.return_value = 'beep'
        # A filename may be a callable, in which case it is called and
        # the result used, and are cast to strings.
        reactive.helpers.any_file_changed(['one', lambda: 'two', 3])
        file_hash.assert_has_calls([mock.call('one', hash_type='md5'),
                                    mock.call('two', hash_type='md5'),
                                    mock.call('3', hash_type='md5')])

    def test_was_invoked(self):
        assert not reactive.helpers.was_invoked('foo')
        assert not reactive.helpers.was_invoked('foo')
        reactive.helpers.mark_invoked('foo')
        assert reactive.helpers.was_invoked('foo')

    def test_data_changed(self):
        assert reactive.helpers.data_changed('foo', {'foo': 'FOO', 'bar': u'\ua000BAR'})
        assert not reactive.helpers.data_changed('foo', {'foo': 'FOO', 'bar': u'\ua000BAR'})
        assert reactive.helpers.data_changed('bar', {'foo': 'FOO', 'bar': u'\ua000BAR'})
        assert reactive.helpers.data_changed('foo', {'foo': 'QUX', 'bar': u'\ua000BAR'})
        assert not reactive.helpers.data_changed('foo', {'foo': 'QUX', 'bar': u'\ua000BAR'})

    @mock.patch.object(reactive.helpers, 'any_hook')
    def test__hook(self, any_hook):
        pats = ['pat1', 'pat2']

        self.kv.set('reactive.dispatch.phase', 'hooks')
        any_hook.return_value = True
        assert reactive.helpers._hook(pats)
        any_hook.assert_called_once_with(*pats)

        any_hook.reset_mock()
        self.kv.set('reactive.dispatch.phase', 'other')
        any_hook.return_value = True
        assert not reactive.helpers._hook(pats)
        assert not any_hook.called

        any_hook.reset_mock()
        self.kv.set('reactive.dispatch.phase', 'hooks')
        any_hook.return_value = False
        assert not reactive.helpers._hook(pats)
        any_hook.assert_called_once_with('pat1', 'pat2')

    def test__when_all(self):
        test = lambda: reactive.helpers._when_all(['state1', 'state2'])

        self.kv.set('reactive.dispatch.phase', 'hooks')
        assert not test(), 'when_all: hooks; none'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert not test(), 'when_all: other; none'

        self.kv.set('reactive.dispatch.phase', 'hooks')
        reactive.set_flag('state1')
        assert not test(), 'when_all: hooks; one'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert not test(), 'when_all: other; one'

        self.kv.set('reactive.dispatch.phase', 'hooks')
        reactive.set_flag('state2')
        assert not test(), 'when_all: hooks; both'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert test(), 'when_all: other; both'

    def test__when_any(self):
        test = lambda: reactive.helpers._when_any(['state1', 'state2'])

        self.kv.set('reactive.dispatch.phase', 'hooks')
        assert not test(), 'when_any: hooks; none'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert not test(), 'when_any: other; none'

        self.kv.set('reactive.dispatch.phase', 'hooks')
        reactive.set_flag('state1')
        assert not test(), 'when_any: hooks; one'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert test(), 'when_any: other; one'

        self.kv.set('reactive.dispatch.phase', 'hooks')
        reactive.set_flag('state2')
        assert not test(), 'when_any: hooks; both'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert test(), 'when_any: other; both'

    def test__when_none(self):
        test = lambda: reactive.helpers._when_none(['state1', 'state2'])

        self.kv.set('reactive.dispatch.phase', 'hooks')
        assert not test(), 'when_not: hooks; none'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert test(), 'when_none: other; none'

        self.kv.set('reactive.dispatch.phase', 'hooks')
        reactive.set_flag('state1')
        assert not test(), 'when_none: hooks; one'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert not test(), 'when_none: other; one'

        self.kv.set('reactive.dispatch.phase', 'hooks')
        reactive.set_flag('state2')
        assert not test(), 'when_none: hooks; both'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert not test(), 'when_none: other; both'

    def test__when_not_all(self):
        test = lambda: reactive.helpers._when_not_all(['state1', 'state2'])

        self.kv.set('reactive.dispatch.phase', 'hooks')
        assert not test(), 'when_not_all: hooks; none'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert test(), 'when_not_all: other; none'

        self.kv.set('reactive.dispatch.phase', 'hooks')
        reactive.set_flag('state1')
        assert not test(), 'when_not_all: hooks; one'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert test(), 'when_not_all: other; one'

        self.kv.set('reactive.dispatch.phase', 'hooks')
        reactive.set_flag('state2')
        assert not test(), 'when_not_all: hooks; both'

        self.kv.set('reactive.dispatch.phase', 'other')
        assert not test(), 'when_not_all: other; both'

    @mock.patch('charmhelpers.core.hookenv.hook_name')
    def test_restricted_hook(self, hook_name):
        self.kv.set('reactive.dispatch.phase', 'restricted')
        hook_name.return_value = 'meter-status-changed'
        assert not reactive.helpers._restricted_hook('bar')
        assert not reactive.helpers._restricted_hook('config-changed')
        assert reactive.helpers._restricted_hook('meter-status-changed')

        self.kv.set('reactive.dispatch.phase', 'other')
        hook_name.return_value = 'meter-status-changed'
        assert not reactive.helpers._restricted_hook('bar')
        assert not reactive.helpers._restricted_hook('config-changed')
        assert not reactive.helpers._restricted_hook('meter-status-changed')
