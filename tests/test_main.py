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

import unittest

import mock

from charmhelpers.core import unitdata
from charms import reactive


class TestReactiveMain(unittest.TestCase):
    @mock.patch.object(unitdata, '_KV')
    @mock.patch.object(reactive.bus, 'dispatch')
    @mock.patch.object(reactive.bus, 'discover')
    @mock.patch.object(reactive, 'hookenv')
    def test_main(self, hookenv, discover, dispatch, _KV):
        hookenv.hook_name.return_value = 'hook_name'
        reactive.main()
        hookenv.log.assert_called_once_with('Reactive main running for hook hook_name', level=hookenv.INFO)
        discover.assert_called_once_with()
        dispatch.assert_called_once_with()
        _KV.flush.assert_called_once_with()
