#!/bin/sh
# Install the complete Node.js runtime bundle on a BB10 device over SSH.
# This is the recommended install method: it includes node.bin, the patched
# libuv, the C++ runtime libraries and npm/npx.
#
# Required:
#   BUNDLE       local bb10-node24-runtime-v24.22.1.tar.gz
# Optional:
#   DEVICE_IP    default 169.254.0.1
#   DEVICE_USER  default devuser
#   KEY          private key (default ~/.ssh/bb10_rsa)
#
# The previous runtime directory is moved to nodedist.backup.<timestamp>.
set -e

: "${BUNDLE:?set BUNDLE to the runtime tar.gz}"
DEVICE_IP=${DEVICE_IP:-169.254.0.1}
DEVICE_USER=${DEVICE_USER:-devuser}
KEY=${KEY:-$HOME/.ssh/bb10_rsa}

[ -r "$BUNDLE" ] || { echo "bundle not readable: $BUNDLE" >&2; exit 1; }
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

echo "uploading $BUNDLE -> $DEVICE_USER@$DEVICE_IP:/tmp/bb10-node24-runtime.tar.gz"
scp_run "$BUNDLE" "$DEVICE_USER@$DEVICE_IP:/tmp/bb10-node24-runtime.tar.gz"

echo "installing runtime under /accounts/1000/shared/misc/nodedist"
ssh_run "$DEVICE_USER@$DEVICE_IP" '
  set -e
  MISC=/accounts/1000/shared/misc
  TS=$(date +%Y%m%d-%H%M%S)
  if [ -d "$MISC/nodedist" ]; then
    mv "$MISC/nodedist" "$MISC/nodedist.backup.$TS"
    echo "previous runtime moved to $MISC/nodedist.backup.$TS"
  fi
  tar -xzf /tmp/bb10-node24-runtime.tar.gz -C "$MISC"
  rm -f /tmp/bb10-node24-runtime.tar.gz
  chmod 755 "$MISC/nodedist/bin/node" "$MISC/nodedist/bin/npm" \
            "$MISC/nodedist/bin/npx" "$MISC/nodedist/bin/node.bin"
  LD_LIBRARY_PATH="$MISC/nodedist/lib" "$MISC/nodedist/bin/node" -v
  echo "Add to PATH:  export PATH=$MISC/nodedist/bin:\$PATH"
'

echo "done. Rollback: move nodedist.backup.<timestamp> back to nodedist"
