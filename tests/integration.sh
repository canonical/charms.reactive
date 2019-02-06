#!/bin/bash

set -eux

PATH=/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

nonce=$(pwgen -A 8 1)
model="reactive-$nonce"
CHARM_DIR=$HOME/$model/charms
BUILD_DIR=$HOME/$model/builds

mkdir "$HOME/$model"
mkdir "$CHARM_DIR"
mkdir "$BUILD_DIR"

charm pull-source cs:ghost "$CHARM_DIR"
charm build "$CHARM_DIR/ghost" --build-dir "$BUILD_DIR"

juju add-model "$model"
juju switch "$model"
wget 'https://api.jujucharms.com/charmstore/v5/ghost/resource/ghost-stable' -O ghost.zip
juju deploy "$BUILD_DIR/ghost" --series=xenial
juju deploy cs:haproxy
juju attach ghost ghost-stable=./ghost.zip
juju add-relation ghost haproxy
juju-wait -vw
