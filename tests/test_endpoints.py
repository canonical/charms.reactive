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

import sys
import mock
import tempfile
import unittest
from pathlib import Path

from charmhelpers.core import unitdata
from charms.reactive import (
    Endpoint,
    set_flag,
    is_flag_set,
    clear_flag,
    register_trigger,
)
from charms.reactive.bus import discover, dispatch, Handler


class TestEndpoint(unittest.TestCase):
    def setUp(self):
        tests_dir = Path(__file__).parent

        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.close()
        self.test_db = Path(tf.name)
        unitdata._KV = self.kv = unitdata.Storage(str(self.test_db))

        self.log_p = mock.patch('charmhelpers.core.hookenv.log')
        self.log_p.start()

        self.charm_dir = str(tests_dir / 'data')
        self.charm_dir_p = mock.patch('charmhelpers.core.hookenv.charm_dir')
        mcharm_dir = self.charm_dir_p.start()
        mcharm_dir.side_effect = lambda: self.charm_dir

        self.hook_name = 'upgrade-charm'
        self.hook_name_p = mock.patch('charmhelpers.core.hookenv.hook_name')
        mhook_name = self.hook_name_p.start()
        mhook_name.side_effect = lambda: self.hook_name

        self.local_unit_p = mock.patch('charmhelpers.core.hookenv.local_unit',
                                       mock.MagicMock(return_value='local/0'))
        self.local_unit_p.start()

        self.app_name_p = mock.patch('charmhelpers.core.hookenv.application_name',
                                     mock.MagicMock(return_value='local'))
        self.app_name_p.start()

        self.remote_unit = None
        self.remote_unit_p = mock.patch('charmhelpers.core.hookenv.remote_unit')
        mremote_unit = self.remote_unit_p.start()
        mremote_unit.side_effect = lambda: self.remote_unit

        self.relation_id = None
        self.relation_id_p = mock.patch('charmhelpers.core.hookenv.relation_id')
        mrelation_id = self.relation_id_p.start()
        mrelation_id.side_effect = lambda: self.relation_id

        self.relations = {
            'test-endpoint': [
                {
                    'local': {'app-key': 'value'},
                    'local/0': {'key': 'value'},
                    'unit': {'simple': 'value', 'complex': '[1, 2]'},
                    'unit/0': {'foo': 'yes'},
                    'unit/1': {},
                },
                {
                    'local': {},
                    'local/0': {},
                    'unit': {},
                    'unit/0': {'bar': '[1, 2]'},
                    'unit/1': {'foo': 'no'},
                },
            ],
        }

        def _rel(rid):
            rn, ri = rid.split(':')
            return self.relations[rn][int(ri)]

        def _rel_get(attribute=None, unit=None, rid=None, app=None):
            data = _rel(rid)[unit or app]
            if attribute is not None:
                return data[attribute]
            else:
                return data

        self.rel_ids_p = mock.patch('charmhelpers.core.hookenv.relation_ids')
        rel_ids_m = self.rel_ids_p.start()
        rel_ids_m.side_effect = lambda endpoint: [
            '{}:{}'.format(endpoint, i) for i in range(
                len(self.relations.get(endpoint, [])))]
        self.rel_units_p = mock.patch('charmhelpers.core.hookenv.related_units')
        rel_units_m = self.rel_units_p.start()
        rel_units_m.side_effect = lambda rid: [
            key for key in _rel(rid).keys()
            if (not key.startswith('local') and
                '/' in key and  # exclude apps
                not _rel(rid)[key].get('departed'))]
        self.rel_get_p = mock.patch('charmhelpers.core.hookenv.relation_get')
        rel_get_m = self.rel_get_p.start()
        rel_get_m.side_effect = _rel_get

        self.rel_set_p = mock.patch('charmhelpers.core.hookenv.relation_set')
        self.relation_set = self.rel_set_p.start()

        self.data_changed_p = mock.patch('charms.reactive.endpoints.data_changed')
        self.data_changed = self.data_changed_p.start()

        self.atexit_p = mock.patch('charmhelpers.core.hookenv.atexit')
        self.atexit = self.atexit_p.start()

        self.sysm_p = mock.patch.dict(sys.modules)
        self.sysm_p.start()

        self.kv.set('reactive.endpoints.departed.test-endpoint', [
            {
                'relation': 'test-endpoint:1',
                'unit_name': 'unit/3',
                'data': {'departed': 'true'},
            },
            {
                'relation': 'test-endpoint:2',
                'unit_name': 'unit/4',
                'data': {'departed': 'true'},
            },
        ])

        discover()

    def tearDown(self):
        self.log_p.stop()
        self.charm_dir_p.stop()
        self.hook_name_p.stop()
        self.local_unit_p.stop()
        self.remote_unit_p.stop()
        self.rel_ids_p.stop()
        self.rel_units_p.stop()
        self.rel_get_p.stop()
        self.rel_set_p.stop()
        self.data_changed_p.stop()
        self.atexit_p.stop()
        self.test_db.unlink()
        self.sysm_p.stop()
        Endpoint._endpoints.clear()
        Handler._HANDLERS.clear()

    def test_from_name(self):
        Endpoint._endpoints['foo'] = endpoint = Endpoint('foo')

        self.assertIs(Endpoint.from_name('foo'), endpoint)
        self.assertIsNone(Endpoint.from_name('bar'))

    def test_from_flag(self):
        Endpoint._endpoints['foo'] = endpoint = Endpoint('foo')

        self.assertIsNone(Endpoint.from_flag('foo'))
        self.assertIsNone(Endpoint.from_flag('bar.qux.zod'))

        # should return None for unset flag
        self.assertIsNone(Endpoint.from_flag('endpoint.foo.qux'))

        # once flag is set, should return the endpoint
        set_flag('endpoint.foo.qux')
        self.assertIs(Endpoint.from_flag('endpoint.foo.qux'), endpoint)

        set_flag('foo.qux')
        self.assertIs(Endpoint.from_flag('foo.qux'), endpoint)

    def test_startup(self):
        assert not is_flag_set('endpoint.test-endpoint.joined')
        assert not is_flag_set('endpoint.test-endpoint.changed')
        assert not is_flag_set('endpoint.test-endpoint.changed.foo')

        set_flag('endpoint.test-endpoint2.joined')
        set_flag('alias.test-endpoint2.joined')

        def _register_triggers(self):
            joined_flag = self.expand_name('endpoint.{endpoint_name}.joined')
            alias_joined_flag = self.expand_name('alias.{endpoint_name}.joined')
            register_trigger(when=joined_flag, set_flag=alias_joined_flag)
            register_trigger(when_not=joined_flag, clear_flag=alias_joined_flag)

        self.data_changed.return_value = True
        with mock.patch.object(Endpoint, 'register_triggers',
                               _register_triggers):
            Endpoint._startup()
        assert Endpoint.from_name('test-endpoint') is not None
        assert Endpoint.from_name('test-endpoint').endpoint_name == 'test-endpoint'
        assert Endpoint.from_name('test-endpoint').is_joined
        assert Endpoint.from_name('test-endpoint').joined  # deprecated
        assert is_flag_set('endpoint.test-endpoint.joined')
        assert is_flag_set('endpoint.test-endpoint.changed')
        assert is_flag_set('endpoint.test-endpoint.changed.foo')
        assert Endpoint.from_name('test-endpoint2') is not None
        assert Endpoint.from_name('test-endpoint2').endpoint_name == 'test-endpoint2'
        assert not Endpoint.from_name('test-endpoint2').is_joined
        assert not Endpoint.from_name('test-endpoint2').joined  # deprecated
        assert not is_flag_set('endpoint.test-endpoint2.joined')
        assert not is_flag_set('endpoint.test-endpoint2.changed')
        assert not is_flag_set('endpoint.test-endpoint2.changed.foo')
        assert is_flag_set('alias.test-endpoint.joined')
        assert not is_flag_set('alias.test-endpoint2.joined')
        assert not is_flag_set('alias.test-endpoint3.joined')
        self.assertEqual(self.atexit.call_args_list, [
            mock.call(Endpoint.from_name('test-endpoint').relations[0]._flush_data),
            mock.call(Endpoint.from_name('test-endpoint').relations[1]._flush_data),
        ])

        # already joined, not relation hook
        clear_flag('endpoint.test-endpoint.changed')
        clear_flag('endpoint.test-endpoint.changed.foo')
        Endpoint._startup()
        assert not is_flag_set('endpoint.test-endpoint.changed')
        assert not is_flag_set('endpoint.test-endpoint.changed.foo')

        # relation hook
        self.hook_name = 'test-endpoint-relation-joined'
        clear_flag('endpoint.test-endpoint.changed')
        clear_flag('endpoint.test-endpoint.changed.foo')
        Endpoint._startup()
        assert is_flag_set('endpoint.test-endpoint.changed')
        assert is_flag_set('endpoint.test-endpoint.changed.foo')

        # not already joined
        self.hook_name = 'upgrade-charm'
        clear_flag('endpoint.test-endpoint.joined')
        clear_flag('endpoint.test-endpoint.changed')
        clear_flag('endpoint.test-endpoint.changed.foo')
        Endpoint._startup()
        assert is_flag_set('endpoint.test-endpoint.changed')
        assert is_flag_set('endpoint.test-endpoint.changed.foo')

        # data not changed
        self.data_changed.return_value = False
        clear_flag('endpoint.test-endpoint.joined')
        clear_flag('endpoint.test-endpoint.changed')
        clear_flag('endpoint.test-endpoint.changed.foo')
        Endpoint._startup()
        assert not is_flag_set('endpoint.test-endpoint.changed')
        assert not is_flag_set('endpoint.test-endpoint.changed.foo')

    def test_collections(self):
        Endpoint._startup()
        tep = Endpoint.from_name('test-endpoint')

        self.assertEqual(len(tep.relations), 2)
        self.assertEqual(len(tep.relations[0].joined_units), 2)
        self.assertEqual(len(tep.relations[1].joined_units), 2)
        self.assertEqual(tep.relations['test-endpoint:0'].relation_id, 'test-endpoint:0')
        self.assertEqual(len(tep.all_joined_units), 4)
        self.assertEqual([u.unit_name for r in tep.relations for u in r.joined_units],
                         ['unit/0', 'unit/1', 'unit/0', 'unit/1'])
        self.assertEqual([u.unit_name for u in tep.all_joined_units],
                         ['unit/0', 'unit/1', 'unit/0', 'unit/1'])
        self.assertEqual(tep.relations[0].joined_units['unit/1'].unit_name, 'unit/1')
        self.assertEqual(tep.relations[0].relation_id, 'test-endpoint:0')
        self.assertEqual(tep.relations[0].endpoint_name, 'test-endpoint')
        self.assertEqual(tep.relations[0].application_name, 'unit')
        self.assertEqual(tep.relations[0].joined_units[0].unit_name, 'unit/0')
        self.assertEqual(tep.all_joined_units.keys(), ['unit/0', 'unit/1', 'unit/0', 'unit/1'])
        self.assertEqual(tep.relations[0].joined_units.keys(), ['unit/0', 'unit/1'])
        self.assertEqual(tep.relations.keys(), ['test-endpoint:0', 'test-endpoint:1'])
        self.assertIs(tep.all_units, tep.all_joined_units)  # deprecated
        self.assertIs(tep.relations[0].units, tep.relations[0].joined_units)  # deprecated

    def test_departed(self):
        # clean up some units for this test
        del self.relations['test-endpoint'][0]['unit/1']
        del self.relations['test-endpoint'][1]['unit/0']
        # add unit/2 as joined
        self.relations['test-endpoint'][0]['unit/2'] = {'departed': 'yes'}
        # but set current hook as unit/2 departing
        self.hook_name = 'test-endpoint-relation-departed'
        self.relation_id = 'test-endpoint:0'
        self.remote_unit = 'unit/2'
        Endpoint._startup()
        tep = Endpoint.from_name('test-endpoint')

        self.assertCountEqual(tep.relations.keys(), ['test-endpoint:0', 'test-endpoint:1'])
        self.assertCountEqual(tep.all_joined_units.keys(), ['unit/0', 'unit/1'])
        self.assertCountEqual(tep.all_departed_units.keys(), ['unit/2', 'unit/3', 'unit/4'])
        self.assertEqual(tep.all_departed_units['unit/2'].received_raw['departed'], 'yes')
        self.assertIs(tep.all_departed_units['unit/3'].received['departed'], True)

        self.assertCountEqual(self.kv.get('reactive.endpoints.departed.test-endpoint'), [
            {
                'relation': 'test-endpoint:0',
                'unit_name': 'unit/2',
                'data': {
                    'departed': 'yes',
                },
            },
            {
                'relation': 'test-endpoint:1',
                'unit_name': 'unit/3',
                'data': {
                    'departed': 'true',
                },
            },
            {
                'relation': 'test-endpoint:2',
                'unit_name': 'unit/4',
                'data': {
                    'departed': 'true',
                },
            },
        ])
        del tep.all_departed_units['unit/3']
        self.assertCountEqual(self.kv.get('reactive.endpoints.departed.test-endpoint'), [
            {
                'relation': 'test-endpoint:0',
                'unit_name': 'unit/2',
                'data': {
                    'departed': 'yes',
                },
            },
            {
                'relation': 'test-endpoint:2',
                'unit_name': 'unit/4',
                'data': {
                    'departed': 'true',
                },
            },
        ])
        del tep.all_departed_units['unit/2']
        del tep.all_departed_units['unit/4']
        self.assertIsNone(self.kv.get('reactive.endpoints.departed.test-endpoint'))

        # test relation moves to broken during last departed hook
        self.relation_id = 'test-endpoint:1'
        self.remote_unit = 'unit/1'
        self.relations['test-endpoint'][1]['unit/1'] = {'departed': 'yes'}
        Endpoint._startup()
        tep = Endpoint.from_name('test-endpoint')
        self.assertEqual(tep.relations.keys(), ['test-endpoint:0'])

    def test_receive(self):
        Endpoint._startup()
        tep = Endpoint.from_name('test-endpoint')

        self.assertEqual(tep.all_joined_units.received_raw, {'foo': 'yes',
                                                             'bar': '[1, 2]'})
        self.assertEqual(tep.all_joined_units.received, {'foo': 'yes',
                                                         'bar': [1, 2]})
        self.assertEqual(tep.relations[0].joined_units.received_raw, {'foo': 'yes'})
        self.assertEqual(tep.relations[1].joined_units.received_raw, {'foo': 'no',
                                                                      'bar': '[1, 2]'})
        self.assertEqual(tep.relations[0].joined_units.received, {'foo': 'yes'})
        self.assertEqual(tep.relations[1].joined_units.received, {'foo': 'no',
                                                                  'bar': [1, 2]})
        self.assertEqual(tep.relations[0].joined_units[0].received_raw, {'foo': 'yes'})
        self.assertEqual(tep.relations[0].joined_units[1].received_raw, {})
        self.assertEqual(tep.relations[1].joined_units[0].received_raw, {'bar': '[1, 2]'})
        self.assertEqual(tep.relations[1].joined_units[1].received_raw, {'foo': 'no'})
        self.assertEqual(tep.relations[0].joined_units[0].received, {'foo': 'yes'})
        self.assertEqual(tep.relations[0].joined_units[1].received, {})
        self.assertEqual(tep.relations[1].joined_units[0].received, {'bar': [1, 2]})
        self.assertEqual(tep.relations[1].joined_units[1].received, {'foo': 'no'})

        self.assertEqual(tep.all_joined_units.received_raw['bar'], '[1, 2]')
        self.assertEqual(tep.all_joined_units.received_raw.get('bar'), '[1, 2]')
        self.assertEqual(tep.all_joined_units.received['bar'], [1, 2])
        self.assertEqual(tep.all_joined_units.received.get('bar'), [1, 2])
        self.assertIsNone(tep.all_joined_units.received_raw['none'])
        self.assertEqual(tep.all_joined_units.received_raw.get('none', 'default'), 'default')
        self.assertIsNone(tep.all_joined_units.received['none'])
        self.assertEqual(tep.all_joined_units.received.get('none', 'default'), 'default')

        assert not tep.all_joined_units.received_raw.writeable
        assert not tep.all_joined_units.received.writeable

        with self.assertRaises(ValueError):
            tep.all_joined_units.received_raw['foo'] = 'nope'

        with self.assertRaises(ValueError):
            tep.relations[0].joined_units.received_raw['foo'] = 'nope'

        with self.assertRaises(ValueError):
            tep.relations[0].joined_units[0].received_raw['foo'] = 'nope'

        with self.assertRaises(ValueError):
            tep.all_joined_units.received['foo'] = 'nope'

        with self.assertRaises(ValueError):
            tep.relations[0].joined_units.received['foo'] = 'nope'

        with self.assertRaises(ValueError):
            tep.relations[0].joined_units[0].received['foo'] = 'nope'

    def test_receive_app(self):
        Endpoint._startup()
        tep = Endpoint.from_name('test-endpoint')

        self.assertEqual(tep.relations[0].received_app_raw, {'simple': 'value', 'complex': '[1, 2]'})
        self.assertEqual(tep.relations[1].received_app_raw, {})
        self.assertEqual(tep.relations[0].received_app, {'simple': 'value', 'complex': [1, 2]})
        self.assertEqual(tep.relations[1].received_app, {})

        assert not tep.relations[0].received_app_raw.writeable
        assert not tep.relations[1].received_app_raw.writeable
        assert not tep.relations[0].received_app.writeable
        assert not tep.relations[1].received_app.writeable

        with self.assertRaises(ValueError):
            tep.relations[0].received_app_raw['simple'] = 'nope'

        with self.assertRaises(ValueError):
            tep.relations[1].received_app_raw['simple'] = 'nope'

        with self.assertRaises(ValueError):
            tep.relations[0].received_app['simple'] = 'nope'

        with self.assertRaises(ValueError):
            tep.relations[1].received_app['simple'] = 'nope'

    def test_to_publish(self):
        Endpoint._startup()
        tep = Endpoint.from_name('test-endpoint')
        rel = tep.relations[0]

        self.assertEqual(rel.to_publish_raw, {'key': 'value'})
        rel._flush_data()
        assert not self.relation_set.called

        rel.to_publish_raw['key'] = 'new-value'
        rel._flush_data()
        self.relation_set.assert_called_once_with('test-endpoint:0', {'key': 'new-value'})

        self.relation_set.reset_mock()
        rel.to_publish['key'] = {'new': 'complex'}
        rel._flush_data()
        self.relation_set.assert_called_once_with('test-endpoint:0', {'key': '{"new": "complex"}'})

        rel.to_publish_raw.update({'key': 'new-new'})
        self.assertEqual(rel.to_publish_raw, {'key': 'new-new'})

        rel.to_publish.update({'key': {'new': 'new'}})
        self.assertEqual(rel.to_publish_raw, {'key': '{"new": "new"}'})

        assert 'foo' not in rel.to_publish
        assert rel.to_publish.get('foo', 'one') == 'one'
        assert 'foo' not in rel.to_publish
        assert rel.to_publish.setdefault('foo', 'two') == 'two'
        assert 'foo' in rel.to_publish
        assert rel.to_publish['foo'] == 'two'
        del rel.to_publish['foo']
        assert 'foo' not in rel.to_publish
        with self.assertRaises(KeyError):
            del rel.to_publish['foo']
        assert 'foo' not in rel.to_publish
        assert rel.to_publish['foo'] is None

    def test_to_publish_app(self):
        Endpoint._startup()
        tep = Endpoint.from_name('test-endpoint')
        rel = tep.relations[0]

        self.assertEqual(rel.to_publish_app_raw, {'app-key': 'value'})
        rel._flush_data()
        assert not self.relation_set.called

        rel.to_publish_app_raw['app-key'] = 'new-value'
        rel._flush_data()
        self.relation_set.assert_called_once_with('test-endpoint:0', {'app-key': 'new-value'}, app=True)

        self.relation_set.reset_mock()
        rel.to_publish_app['app-key'] = {'new': 'complex'}
        rel._flush_data()
        self.relation_set.assert_called_once_with('test-endpoint:0', {'app-key': '{"new": "complex"}'}, app=True)

        rel.to_publish_app.update({'app-key': 'new-new'})
        self.assertEqual(rel.to_publish_app, {'app-key': 'new-new'})

        rel.to_publish_app.update({'app-key': {'new': 'new'}})
        self.assertEqual(rel.to_publish_app, {'app-key': {"new": "new"}})

        assert 'foo' not in rel.to_publish
        assert rel.to_publish.get('foo', 'one') == 'one'
        assert 'foo' not in rel.to_publish
        assert rel.to_publish.setdefault('foo', 'two') == 'two'
        assert 'foo' in rel.to_publish
        assert rel.to_publish['foo'] == 'two'
        del rel.to_publish['foo']
        assert 'foo' not in rel.to_publish
        with self.assertRaises(KeyError):
            del rel.to_publish['foo']
        assert 'foo' not in rel.to_publish
        assert rel.to_publish['foo'] is None

    def test_handlers(self):
        Handler._HANDLERS = {k: h for k, h in Handler._HANDLERS.items()
                             if hasattr(h, '_action') and
                             h._action.__qualname__.startswith('TestAltRequires.')}
        assert Handler._HANDLERS
        preds = [h._predicates[0].args[0][0] for h in Handler.get_handlers()]
        for pred in preds:
            self.assertRegex(pred, r'^endpoint.test-endpoint.')

        self.data_changed.return_value = False
        Endpoint._startup()
        tep = Endpoint.from_name('test-endpoint')

        self.assertCountEqual(tep.invocations, [])
        dispatch()
        self.assertCountEqual(tep.invocations, [
            'joined: test-endpoint',
        ])

        tep.invocations.clear()
        clear_flag('endpoint.test-endpoint.joined')
        clear_flag('endpoint.test-endpoint.changed')
        clear_flag('endpoint.test-endpoint.changed.foo')
        clear_flag('endpoint.test-endpoint2.joined')
        clear_flag('endpoint.test-endpoint2.changed')
        clear_flag('endpoint.test-endpoint2.changed.foo')
        self.data_changed.return_value = True
        Endpoint._startup()
        dispatch()
        self.assertCountEqual(tep.invocations, [
            'joined: test-endpoint',
            'changed: test-endpoint',
            'changed.foo: test-endpoint',
        ])

        tep.invocations.clear()
        clear_flag('endpoint.test-endpoint.joined')
        clear_flag('endpoint.test-endpoint.changed')
        clear_flag('endpoint.test-endpoint.changed.foo')
        clear_flag('endpoint.test-endpoint2.joined')
        clear_flag('endpoint.test-endpoint2.changed')
        clear_flag('endpoint.test-endpoint2.changed.foo')
        self.relations['test-endpoint2'] = [
            {
                'unit/0': {'foo': 'yes'},
                'unit/1': {},
            },
            {
                'unit/0': {},
                'unit/1': {'foo': 'no'},
            },
        ]
        Endpoint._startup()
        dispatch()
        self.assertCountEqual(tep.invocations, [
            'joined: test-endpoint',
            'joined: test-endpoint2',
            'changed: test-endpoint',
            'changed: test-endpoint2',
            'changed.foo: test-endpoint',
            'changed.foo: test-endpoint2',
        ])
