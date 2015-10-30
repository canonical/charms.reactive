from charms.reactive import when
from charms.reactive import set_state


@when('test')
def nested():
    set_state('nested')
