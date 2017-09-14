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
from charms.reactive import context, Endpoint, is_flag_set, clear_flag
from charms.reactive.bus import discover, dispatch, Handler


class TestEndpoint(unittest.TestCase):
    def setUp(self):
        tests_dir = Path(__file__).parent

        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.close()
        self.test_db = Path(tf.name)
        unitdata._KV = self.kv = unitdata.Storage(str(self.test_db))

        self.charm_dir = str(tests_dir / 'data')
        self.charm_dir_p = mock.patch('charmhelpers.core.hookenv.charm_dir')
        mcharm_dir = self.charm_dir_p.start()
        mcharm_dir.side_effect = lambda: self.charm_dir

        self.relations = {
            'test-endpoint': [
                {
                    'unit/0': {'foo': 'yes'},
                    'unit/1': {},
                },
                {
                    'unit/0': {},
                    'unit/1': {'foo': 'no'},
                },
            ],
        }
        self.rel_ids_p = mock.patch('charmhelpers.core.hookenv.relation_ids')
        rel_ids_m = self.rel_ids_p.start()
        rel_ids_m.side_effect = lambda endpoint: [
            '{}:{}'.format(endpoint, i) for i in range(
                len(self.relations.get(endpoint, [])))]
        self.rel_units_p = mock.patch('charmhelpers.core.hookenv.related_units')
        rel_units_m = self.rel_units_p.start()
        rel_units_m.side_effect = lambda rid: (
            self.relations[rid.split(':')[0]][int(rid.split(':')[1])].keys())
        self.rel_get_p = mock.patch('charmhelpers.core.hookenv.relation_get')
        rel_get_m = self.rel_get_p.start()
        rel_get_m.side_effect = lambda unit, rid: (
            self.relations[rid.split(':')[0]][int(rid.split(':')[1])][unit])

        self.data_changed_p = mock.patch('charms.reactive.altrelations.data_changed')
        self.data_changed = self.data_changed_p.start()

        self.sysm_p = mock.patch.dict(sys.modules)
        self.sysm_p.start()

        discover()

    def tearDown(self):
        self.charm_dir_p.stop()
        self.rel_ids_p.stop()
        self.rel_units_p.stop()
        self.rel_get_p.stop()
        self.data_changed_p.stop()
        self.test_db.unlink()
        self.sysm_p.stop()
        Handler._HANDLERS.clear()

    def test_startup(self):
        assert not is_flag_set('relations.test-endpoint.joined')
        assert not is_flag_set('relations.test-endpoint.changed')
        assert not is_flag_set('relations.test-endpoint.changed.foo')

        self.data_changed.return_value = True
        Endpoint._startup()
        assert context.endpoints.test_endpoint is not None
        assert context.endpoints.test_endpoint.relation_name == 'test-endpoint'
        assert is_flag_set('relations.test-endpoint.joined')
        assert is_flag_set('relations.test-endpoint.changed')
        assert is_flag_set('relations.test-endpoint.changed.foo')

        clear_flag('relations.test-endpoint.changed')
        clear_flag('relations.test-endpoint.changed.foo')
        self.data_changed.return_value = False
        Endpoint._startup()
        assert not is_flag_set('relations.test-endpoint.changed')
        assert not is_flag_set('relations.test-endpoint.changed.foo')

        self.relations = {}
        Endpoint._startup()
        assert context.endpoints.test_endpoint is None
        assert not is_flag_set('relations.test-endpoint.joined')
        assert not is_flag_set('relations.test-endpoint.changed')
        assert not is_flag_set('relations.test-endpoint.changed.foo')

    def test_handlers(self):
        Handler._HANDLERS = {k: h for k, h in Handler._HANDLERS.items()
                             if hasattr(h, '_action') and
                             h._action.__qualname__.startswith('TestAltRequires.')}
        assert Handler._HANDLERS
        preds = [h._predicates[0].args[0][0] for h in Handler.get_handlers()]
        for pred in preds:
            self.assertRegex(pred, r'^relations.test-endpoint.')

        self.data_changed.return_value = False
        Endpoint._startup()

        self.assertCountEqual(context.endpoints.test_endpoint.invocations, [])
        dispatch()
        self.assertCountEqual(context.endpoints.test_endpoint.invocations, [
            'joined: test-endpoint',
        ])

        context.endpoints.test_endpoint.invocations.clear()
        self.data_changed.return_value = True
        Endpoint._startup()
        dispatch()
        self.assertCountEqual(context.endpoints.test_endpoint.invocations, [
            'joined: test-endpoint',
            'changed: test-endpoint',
        ])

        context.endpoints.test_endpoint.invocations.clear()
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
        self.assertCountEqual(context.endpoints.test_endpoint.invocations, [
            'joined: test-endpoint',
            'joined: test-endpoint2',
            'changed: test-endpoint',
            'changed: test-endpoint2',
        ])
