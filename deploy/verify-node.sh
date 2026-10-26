#!/bin/sh
# Verify the installed Node.js on a BB10 device over SSH.
#
# Optional:
#   DEVICE_IP     default 169.254.0.1
#   DEVICE_USER   default devuser
#   KEY           private key (default ~/.ssh/bb10_rsa)
set -e

DEVICE_IP=${DEVICE_IP:-169.254.0.1}
DEVICE_USER=${DEVICE_USER:-devuser}
KEY=${KEY:-$HOME/.ssh/bb10_rsa}

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

ssh_run "$DEVICE_USER@$DEVICE_IP" 'sh -s' <<'REMOTE'
set -e
. "$HOME/.profile" 2>/dev/null || . /accounts/devuser/.profile 2>/dev/null || true

echo "--- versions"
node -v
npm -v
npx -v

echo "--- unicode properties"
node -e 'console.log(/\p{Emoji}/u.test("😀"), /\p{L}\p{N}/u.test("a1"))'

echo "--- Intl.Segmenter (grapheme)"
node -e 'const s=new Intl.Segmenter("en",{granularity:"grapheme"}); console.log(JSON.stringify([...s.segment("a👍🏽b")].map(x=>x.segment)))'

echo "--- Intl.Segmenter (word)"
node -e 'const s=new Intl.Segmenter("en",{granularity:"word"}); console.log(JSON.stringify([...s.segment("hello world")].map(x=>x.segment)))'

echo "--- GC stress"
node --expose-gc -e 'let k=[];for(let i=0;i<300;i++){for(let j=0;j<20000;j++)k.push({j,s:"x"+j});if(i%3===0)global.gc();k.length=0;}console.log("gc ok")'

echo "--- ok"
REMOTE

cat <<'NOTE'

For a TTY check, run manually:
  ssh -tt -i "$KEY" <user>@<ip> '. "$HOME/.profile"; node -v; npm --version'
NOTE
