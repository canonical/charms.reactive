#!/bin/bash

set -eux

PATH=/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

tmpdir="$(mktemp -d)"
arch=$(dpkg --print-architecture)

# Build a wheel so that the test charm can be built using
# the local version of the charms.reactive library
cp setup.cfg setup.cfg.bak
cat << EOF >> setup.cfg

[build]
build-base = $tmpdir/build

[egg_info]
egg-base = $tmpdir
EOF

python3 setup.py bdist_wheel
wheel=$(ls -1 dist/)
mv dist/$wheel tests/data/
mv setup.cfg.bak setup.cfg

# Make sure the built charm is using the local version of charms.reactive
echo "charms.reactive @ file:///root/parts/charm/build/$wheel" > tests/data/wheelhouse.txt

pushd tests/data
charmcraft -v pack
popd

# Cleanup the wheelhouse.txt file.
rm tests/data/wheelhouse.txt
juju deploy ./tests/data/test-charm_$arch.charm
juju-wait -vw
