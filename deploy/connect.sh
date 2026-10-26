#!/bin/sh
# Start the qconnDoor tunnel to a BB10 device in Development Mode.
#
# Required:
#   DEVICE_IP        device USB/development IP (often 169.254.0.1)
#   DEVICE_PASSWORD  device screen-lock password
# Optional:
#   KEY              private key path (default ~/.ssh/bb10_rsa)
#   KEY_PUB          public key path (default $KEY.pub)
#   BB10MT           path to bb10mt executable (default: from PATH)
#
# Keep this process running: SSH is only available while qconnDoor is alive.
set -e

: "${DEVICE_IP:?set DEVICE_IP (e.g. 169.254.0.1)}"
: "${DEVICE_PASSWORD:?set DEVICE_PASSWORD}"
KEY=${KEY:-$HOME/.ssh/bb10_rsa}
KEY_PUB=${KEY_PUB:-$KEY.pub}
BB10MT=${BB10MT:-bb10mt.exe}

[ -r "$KEY_PUB" ] || { echo "public key not readable: $KEY_PUB" >&2; exit 1; }

exec "$BB10MT" connect -i "$DEVICE_IP" -p "$DEVICE_PASSWORD" -k "$KEY_PUB"
