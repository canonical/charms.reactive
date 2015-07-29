#!/bin/bash

if [[ "$0" == "$BASH_SOURCE" ]]; then
    echo 'This file contains helpers for developing reactive charms in Bash.'
    echo
    echo 'Usage:'
    echo
    echo '    source `which reactive.sh`'
    echo
    echo '    @when db.ready cache.ready'
    echo '    function write_configuration() {'
    echo '        db_dsn=$(state_relation_call db.ready uri)'
    echo '        cache_uri=$(state_relation_call cache.ready uri)'
    echo '        chlp render_template db_dsn=$db_dsn cache_uri=$cache_uri'
    echo '    }'
    echo
    echo '    @when_not db.ready cache.ready'
    echo '    function report_blocked() {'
    echo '        status-set blocked "Waiting for db and/or cache"'
    echo '    }'
    echo
    echo '    dispatch'
    echo
    echo 'Helpers available:'
    echo
    echo '  @hook PATTERN                Run decorated function if hook matches'
    echo '  @when STATES                 Run decorated function if states are active'
    echo '  @when_not STATES             Run decorated function if states not active'
    echo '  @when_file_changed FILENAME  Run decorated function if file(s) changed'
    echo '  @only_once                   Run decorated function only once'
    echo '  set_state                    Set / activate a state'
    echo '  remove_state                 Remove a state'
    echo '  relation_call                Call a method on a relation by relation name'
    echo '  state_relation_call          Call a method on a relation by active state'
    echo '  all_states                   Check all states are active'
    echo '  any_states                   Check any states are active'
    echo '  name_relation_get            Get a relation value by relation name (vs ID)'
    exit 0
fi

shopt -s expand_aliases

declare REACTIVE_ACTION
declare -A REACTIVE_HANDLERS
declare -A REACTIVE_POST_INVOKE
while [[ $# > 0 ]]; do
    case "$1" in
        --test)
            REACTIVE_ACTION="test"
            shift
            ;;
        --invoke)
            REACTIVE_ACTION="invoke"
            for handler in ${2//,/ }; do
                REACTIVE_HANDLERS[$handler]='true'
            done
            shift
            ;;
        *)  ;;
    esac
    shift
done

function _get_decorated() {
    filename=${BASH_SOURCE[2]}
    lineno=$((BASH_LINENO[1]+1))
    while sed "${lineno}q;d" $filename | grep -qE "^\s*@"; do
        ((lineno++))
    done
    func=$(sed "${lineno}q;d" $filename | sed "s/\(function\)\? *\(.*\) *() *{/\2/")
}

function @decorator() {
    _get_decorated
    decorator="$1"
    handler_id="$filename:$lineno:$func"
    shift
    if [[ "$REACTIVE_ACTION" == "test" ]]; then
        if [ ! ${REACTIVE_HANDLERS[$func]+_} ]; then
            REACTIVE_HANDLERS[$func]='true'
        fi
        case "$decorator" in
            when|when_not|only_once)
                hid_arg="$handler_id"
                ;;
            *)
                hid_arg=""
        esac
        if ! charms.reactive "$decorator" "$hid_arg" "$@"; then
            REACTIVE_HANDLERS[$func]='false'
        fi
    elif [[ "$REACTIVE_ACTION" == "invoke" && "$decorator" == "only_once" ]]; then
        REACTIVE_POST_INVOKE[$func]="charms.reactive mark_invoked '$handler_id'"
    fi
}

function reactive_handler_main() {
    to_invoke=()
    for handler in "${!REACTIVE_HANDLERS[@]}"; do
        if [[ ${REACTIVE_HANDLERS[$handler]} == 'true' ]]; then
            to_invoke+=("$handler")
        fi
    done
    if [[ "$REACTIVE_ACTION" == "test" ]]; then
        if [[ ${#to_invoke[@]} -gt 0 ]]; then
            local IFS=","
            echo "${to_invoke[*]}"
            exit 0
        else
            exit 1
        fi
    elif [[ "$REACTIVE_ACTION" == "invoke" ]]; then
        for handler in "${to_invoke[@]}"; do
            eval "$handler"
            if [[ -n "${REACTIVE_POST_INVOKE[$handler]}" ]]; then
                eval "${REACTIVE_POST_INVOKE[$handler]}"
            fi
        done
    fi
}

alias @hook='@decorator hook'
alias @when='@decorator when'
alias @when_not='@decorator when_not'
alias @when_file_changed='@decorator when_file_changed'
alias @only_once='@decorator only_once'
alias set_state='charms.reactive set_state'
alias remove_state='charms.reactive remove_state'
alias relation_call='charms.reactive relation_call'  # Call a method on a named relation
alias all_states='charms.reactive all_states'
alias any_states='charms.reactive any_states'

function state_relation_call() {
    # Call a method on the relation implementation associated with the
    # given active state.
    state=$1
    method=$2
    shift; shift
    charms.reactive relation_call $(charms.reactive relation_from_state $state) $method "$@"
}

function name_relation_get() {
    # Helper function around relation-get that accepts a relation name in place
    # of a relation ID.
    #
    # Usage: name_relation_get <relation_name> <unit_name> [<key>] [--format=<format>]
    # Note: The --format option must come at the end, if present
    relation_name="$1"
    unit_name="$2"
    key="$3"
    if [[ -z "$key" || "$key" == --* ]]; then
        key="-"
        shift; shift
    else
        shift; shift; shift
    fi
    relid="$(charms.reactive relation_id "$relation_name" "$unit_name")"
    relation-get -r "$relid" "$key" "$unit_name" "$@"
}
