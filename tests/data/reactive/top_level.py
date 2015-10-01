from charms.reactive import hook
from charms.reactive import when
from charms.reactive import when_not
from charms.reactive import set_state
from charms.reactive import remove_state
from charms.reactive.helpers import any_states


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
