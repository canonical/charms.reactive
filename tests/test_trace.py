# Copyright 2018 Canonical Limited.
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

from textwrap import dedent
import unittest
from unittest import mock

from charms import reactive


class TestTracer(unittest.TestCase):
    def test_nulltracer_api(self):
        self._test_api(reactive.trace.NullTracer())

    @mock.patch('charms.reactive.bus._short_action_id')
    @mock.patch('charms.reactive.bus.Handler.get_handlers')
    @mock.patch('charmhelpers.core.hookenv.log')
    def test_logtracer_api(self, log, gh, sid):
        sid.side_effect = lambda x, y: x
        h = reactive.bus.Handler
        gh.side_effect = [
            [h('handler_1')],
            [h('handler_2'), h('handler_3')],
        ]
        self._test_api(reactive.trace.LogTracer())
        # We are not wedded to this format. We should change it if we
        # can come up with something more generally readable. Multiline
        # strings are used to avoid hookenv.log call overhead (juju-log is
        # expensive), but that might be premature optimization.
        log.assert_has_calls([
            mock.call('tracer: starting handler dispatch, 0 flags set', 'DEBUG'),
            mock.call('tracer: hooks phase, 0 handlers queued', 'DEBUG'),
            mock.call(dedent('''\
                      tracer>
                      tracer: set flag flag_a
                      tracer: ++   queue handler handler_1
                      ''').strip(), 'DEBUG'),
            mock.call(dedent('''\
                      tracer>
                      tracer: cleared flag flag_b
                      tracer: ++   queue handler handler_2
                      tracer: ++   queue handler handler_3
                      tracer: -- dequeue handler handler_1
                      ''').strip(), 'DEBUG'),
        ])

    def _test_api(self, imp):
        imp.start_dispatch()
        imp.start_dispatch_phase('hooks', [])
        imp.start_dispatch_iteration(0, [])
        imp.set_flag('flag_a')
        imp.clear_flag('flag_b')
