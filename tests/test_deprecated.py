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

import unittest

from charms.reactive import deprecated


@deprecated.alias('alias')
def target(arg, kw):
    "docstring"
    return arg, kw


class TestDeprecated(unittest.TestCase):
    def test_alias(self):
        self.assertEqual(('arg', 'kw'), target('arg', kw='kw'))
        self.assertEqual(('arg', 'kw'), alias('arg', kw='kw'))  # noqa
        self.assertNotIn('DEPRECATED', target.__doc__)
        self.assertIn('DEPRECATED', alias.__doc__)  # noqa


if __name__ == '__main__':
    unittest.main()
