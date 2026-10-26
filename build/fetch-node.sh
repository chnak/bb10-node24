#!/bin/bash
# Fetch the upstream Node.js source and apply the BB10/QNX patch series.
#
#   bash build/fetch-node.sh
#
# Environment:
#   VERSION   upstream tag to fetch (default v24.22.1)
#   NODE_SRC  where the source tree should live
#             (default /root/nodebuild/node-v24.22.1-icu)
#
# The resulting tree is the one the build scripts in this directory expect.
# `patches/qnx-bb10-node24.patch` is the end state of those patch scripts, so
# after this step most of them are no longer needed. patch_host_mk.py still
# has to run after every ./configure (see docs/BUILD.md section 5.7).
set -e

VERSION=${VERSION:-v24.22.1}
NODE_SRC=${NODE_SRC:-/root/nodebuild/node-v24.22.1-icu}
REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)
PATCH_FILE="$REPO_DIR/patches/qnx-bb10-node24.patch"

[ -f "$PATCH_FILE" ] || { echo "patch file not found: $PATCH_FILE" >&2; exit 1; }

mkdir -p "$(dirname "$NODE_SRC")"
cd "$(dirname "$NODE_SRC")"

if [ ! -f "$NODE_SRC/configure" ]; then
    echo "downloading nodejs $VERSION ..."
    curl -sSL --max-time 900 -O "https://nodejs.org/dist/$VERSION/node-$VERSION.tar.xz"
    tar -xJf "node-$VERSION.tar.xz"
    rm -f "node-$VERSION.tar.xz"
    if [ "$NODE_SRC" != "node-$VERSION" ]; then
        rm -rf "$NODE_SRC"
        mv "node-$VERSION" "$NODE_SRC"
    fi
else
    echo "source already present: $NODE_SRC"
fi

cd "$NODE_SRC"
echo "applying $PATCH_FILE"
patch -p1 < "$PATCH_FILE"

echo
echo "source ready: $NODE_SRC"
echo "next: configure + build (see docs/BUILD.md and docs/ICU-BUILD.md)"
