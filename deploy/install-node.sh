#!/bin/sh
# Install a Node.js binary on a BB10 device over SSH (qconnDoor).
#
# Required:
#   BINARY           local node binary (e.g. ./node.bin.icu2)
# Optional:
#   DEVICE_IP        default 169.254.0.1
#   DEVICE_USER      default devuser
#   KEY              private key (default ~/.ssh/bb10_rsa)
#   REMOTE           default /accounts/1000/shared/misc/nodedist/bin/node.bin
#
# The existing node.bin is backed up once as node.bin.pre-icu.
set -e

: "${BINARY:?set BINARY to the local node binary}"
DEVICE_IP=${DEVICE_IP:-169.254.0.1}
DEVICE_USER=${DEVICE_USER:-devuser}
KEY=${KEY:-$HOME/.ssh/bb10_rsa}
REMOTE=${REMOTE:-/accounts/1000/shared/misc/nodedist/bin/node.bin}
REMOTE_DIR=${REMOTE%/*}
LIB_DIR="$REMOTE_DIR/../lib"

[ -r "$BINARY" ] || { echo "binary not readable: $BINARY" >&2; exit 1; }
[ -r "$KEY" ] || { echo "private key not readable: $KEY" >&2; exit 1; }

ssh_run() {
  ssh -i "$KEY" \
    -o HostKeyAlgorithms=+ssh-rsa \
    -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    -o KexAlgorithms=+diffie-hellman-group1-sha1 \
    -o Ciphers=+aes128-ctr,aes128-cbc,3des-cbc \
    -o MACs=+hmac-sha1 \
    -o StrictHostKeyChecking=no \
    -o BatchMode=yes \
    -o ConnectTimeout=10 \
    "$@"
}

scp_run() {
  scp -i "$KEY" \
    -o HostKeyAlgorithms=+ssh-rsa \
    -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    -o KexAlgorithms=+diffie-hellman-group1-sha1 \
    -o Ciphers=+aes128-ctr,aes128-cbc,3des-cbc \
    -o MACs=+hmac-sha1 \
    -o StrictHostKeyChecking=no \
    -o BatchMode=yes \
    "$@"
}

echo "uploading $BINARY -> $DEVICE_USER@$DEVICE_IP:/tmp/node.bin.new"
scp_run "$BINARY" "$DEVICE_USER@$DEVICE_IP:/tmp/node.bin.new"

echo "installing to $REMOTE"
ssh_run "$DEVICE_USER@$DEVICE_IP" "
  set -e
  [ -f '$REMOTE.pre-icu' ] || cp -p '$REMOTE' '$REMOTE.pre-icu'
  cp -f /tmp/node.bin.new '$REMOTE'
  chmod 755 '$REMOTE'
  rm -f /tmp/node.bin.new
  LD_LIBRARY_PATH='$LIB_DIR' '$REMOTE' -v
"

echo "installed. Backup: $REMOTE.pre-icu"
