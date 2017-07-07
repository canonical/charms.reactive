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

from charms.reactive import hook
from charms.reactive import when
from charms.reactive import when_not
from charms.reactive import set_flag
from charms.reactive import clear_flag
from charms.reactive.helpers import any_flags_set


test_marker = 'top level'


@when('test')
def top_level():
    if any_flags_set('top-level'):
        set_flag('top-level-repeat')
    set_flag('top-level')


@hook('{requires:test}-relation-{changed,joined}')
def test_remove(trel):
    clear_flag('to-remove')


@when_not('to-remove')
def test_remove_not():
    set_flag('test-remove-not')
