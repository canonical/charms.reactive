#!/bin/bash

set -eux

PATH=/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

tmpdir="$(mktemp -d)"

charm build "tests/data" --build-dir "$tmpdir"

juju deploy "$tmpdir/test-charm"
juju-wait -vw
