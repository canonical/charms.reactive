import unittest

import mock

from charmhelpers.core import unitdata
from charms import reactive


class TestReactiveMain(unittest.TestCase):
    @mock.patch.object(unitdata, '_KV')
    @mock.patch.object(reactive.bus, 'dispatch')
    @mock.patch.object(reactive.bus, 'discover')
    @mock.patch.object(reactive.hookenv, 'log')
    @mock.patch.object(reactive.hookenv, 'hook_name')
    def test_main(self, hook_name, log, discover, dispatch, _KV):
        hook_name.return_value = 'hook_name'
        reactive.main()
        log.assert_called_once_with('Reactive main running for hook hook_name', level=reactive.hookenv.INFO)
        discover.assert_called_once_with()
        dispatch.assert_called_once_with()
        _KV.flush.assert_called_once_with()

        _KV.flush.reset_mock()
        discover.side_effect = SystemExit
        self.assertRaises(SystemExit, reactive.main)
        _KV.flush.assert_called_once_with()
