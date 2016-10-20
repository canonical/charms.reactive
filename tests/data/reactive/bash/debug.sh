#!/bin/bash

CHARMS_REACTIVE_TRACE=true

. `dirname $0`/../../../../bin/charms.reactive.sh

@when 'never'
function never_run() {
    >&2 echo This should never run
}

reactive_handler_main
