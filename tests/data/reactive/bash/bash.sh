#!/bin/bash

set -o xtrace
# or set -x

. `dirname $0`/../../../../bin/charms.reactive.sh

@when 'test'
function test_when() {
    if any_states 'bash-when'; then
        set_state 'bash-when-repeat'
    fi
    set_state 'bash-when'
}

@when_any 'test'
function test_when_any() {
    if any_states 'bash-when-any'; then
        set_state 'bash-when-any-repeat'
    fi
    set_state 'bash-when-any'
}

@when 'test-not'
function test_when_neg() {
    if any_states 'bash-when-neg'; then
        set_state 'bash-when-neg-repeat'
    fi
    set_state 'bash-when-neg'
}

@when_not 'test-not'
function test_when_not() {
    if any_states 'bash-when-not'; then
        set_state 'bash-when-not-repeat'
    fi
    set_state 'bash-when-not'
}

@when_not 'test'
function test_when_not_neg() {
    if any_states 'bash-when-not-neg'; then
        set_state 'bash-when-not-neg-repeat'
    fi
    set_state 'bash-when-not-neg'
}

@when_not 'test-not-all'
function test_when_not_all() {
    if any_states 'bash-when-not-all'; then
        set_state 'bash-when-not-all-repeat'
    fi
    set_state 'bash-when-not-all'
}

@when 'test'
@only_once
function test_only_once() {
    if any_states 'bash-only-once'; then
        set_state 'bash-only-once-repeat'
    fi
    set_state 'bash-only-once'
}

@hook '{requires:test}-relation-joined'
function test_hook() {
    if any_states 'bash-hook'; then
        set_state 'bash-hook-repeat'
    fi
    set_state 'bash-hook'
}

@when 'test'
@when_not 'test-not'
function test_multi() {
    if any_states 'bash-multi'; then
        set_state 'bash-multi-repeat'
    fi
    set_state 'bash-multi'
}

@when 'test-not'
@when_not 'test-also-not'
function test_multi_neg() {
    if any_states 'bash-multi-neg'; then
        set_state 'bash-multi-neg-repeat'
    fi
    set_state 'bash-multi-neg'
}

@when 'test'
@when_not 'test'
function test_multi_neg2() {
    if any_states 'bash-multi-neg2'; then
        set_state 'bash-multi-neg2-repeat'
    fi
    set_state 'bash-multi-neg2'
}

reactive_handler_main
