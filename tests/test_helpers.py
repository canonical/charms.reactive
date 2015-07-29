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

    def test__when(self):
        test1 = lambda: reactive.helpers._when('test1', ['state1', 'state2'], invert=False)
        test2 = lambda: reactive.helpers._when('test2', ['state1', 'state2'], invert=True)

        self.kv.set('reactive.dispatch.phase', 'other')
        reactive.bus.StateWatch.iteration(0)
        assert not test1(), 'when: iter 0; none'
        assert test2(), 'when_not: iter 0; none'

        reactive.bus.set_state('state1')
        reactive.bus.set_state('state2')
        assert test1(), 'when: iter 0'
        assert not test2(), 'when_not: iter 0'

        reactive.bus.StateWatch.iteration(1)
        reactive.bus.StateWatch.commit()
        assert test1(), 'when'
        assert not test2(), 'when_not'

        reactive.bus.StateWatch.commit()
        assert not test1(), 'when: no changes'
        assert not test2(), 'when_not: no changes'

        reactive.bus.set_state('state1')
        assert not test1(), 'when: no-op change pending'
        assert not test2(), 'when_not: no-op change pending'
        reactive.bus.StateWatch.commit()
        assert not test1(), 'when: no-op change committed'
        assert not test2(), 'when_not: no-op change committed'

        reactive.bus.StateWatch.commit()
        assert not test1(), 'when: no changes'
        assert not test2(), 'when_not: no changes'

        reactive.bus.remove_state('state1')
        assert not test1(), 'when: remove pending'
        assert not test2(), 'when_not: remove pending'
        reactive.bus.StateWatch.commit()
        assert not test1(), 'when: remove committed'
        assert test2(), 'when_not: remove committed'

        reactive.bus.StateWatch.commit()
        assert not test1(), 'when: no changes'
        assert not test2(), 'when_not: no changes'

        reactive.bus.set_state('state1')
        assert not test1(), 'when: set pending'
        assert not test2(), 'when_not: set pending'
        reactive.bus.StateWatch.commit()
        assert test1(), 'when: set committed'
        assert not test2(), 'when_not: set committed'

        reactive.bus.StateWatch.commit()
        assert not test1(), 'when: no changes'
        assert not test2(), 'when_not: no changes'

        reactive.bus.remove_state('state1')
        reactive.bus.set_state('state1')
        assert not test1(), 'remove + set: pending'
        reactive.bus.StateWatch.commit()
        assert test1(), 'remove + set: committed'
