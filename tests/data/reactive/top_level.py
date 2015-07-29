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
from charms.reactive import set_state
from charms.reactive import remove_state
from charms.reactive.bus import any_states


@when('test')
def top_level():
    if any_states('top-level'):
        set_state('top-level-repeat')
    set_state('top-level')


@hook('{requires:test}-relation-{changed,joined}')
def test_remove(trel):
    remove_state('to-remove')


@when_not('to-remove')
def test_remove_not():
    set_state('test-remove-not')
