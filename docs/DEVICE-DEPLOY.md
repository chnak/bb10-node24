# Deploying Node.js to a BlackBerry 10 device

This guide assumes a rooted/developer-enabled BB10 device and a working
qconnDoor (SSH-over-USB) or SMB connection. Replace every placeholder
(`<...>`) with values for your device. **Never commit real passwords or
private keys.**

## 1. Device prerequisites

1. **Development Mode** is enabled:
   Settings → Security and Privacy → Development Mode. The device must be
   unlocked while connecting.
2. The device has a screen-lock password; qconnDoor uses it to authenticate.
3. On the PC: the BB10 USB drivers and `bb10mt` (qconnDoor) are available.
4. The PC has an SSH key pair. The public key is installed on the device by
   qconnDoor on first connect.

Without Development Mode, qconnDoor returns
`Development mode is not enabled on the device` and `bb10mt` only prints
`Socket disconnected.`

## 2. Start the SSH tunnel

USB Development Mode typically uses `169.254.0.1` on the device and
`169.254.0.2/30` on the PC; the address can change between boots. Check with:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -like '169.254.*' } |
  Format-Table IPAddress,InterfaceAlias,PrefixLength
```

Then start qconnDoor and keep it running (SSH dies when it exits):

```sh
DEVICE_IP=169.254.0.1 \
DEVICE_PASSWORD='<device password>' \
KEY="$HOME/.ssh/bb10_rsa" \
./deploy/connect.sh
```

Verify port 22:

```powershell
Test-NetConnection 169.254.0.1 -Port 22
```

Wi-Fi also works for SMB file transfer (`<phone-ip>:445`, user `BlackBerry`
and the device password) and, with Development Mode enabled, for qconnDoor.

## 3. Device layout

```
/accounts/1000/shared/misc/nodedist/
├── bin/
│   ├── node.bin          # the Node binary
│   ├── node.bin.pre-icu  # backup created by the binary-only installer
│   ├── node              # relocatable wrapper (sets LD_LIBRARY_PATH)
│   ├── npm
│   └── npx
└── lib/
    ├── libuv.so.1        # patched libuv (fcntl/ptsname/dirent)
    ├── libstdc++.so.6
    ├── libgcc_s.so.1
    ├── libbacktrace.so.1
    └── node_modules/npm  # npm 11.19.1
```

`/var/tmp` may be cleared on reboot; keep Node under `/accounts/...`.

## 4. Install

**Recommended: the complete runtime bundle.** It contains Node, npm 11.19.1,
the patched libuv and the C++ runtime libraries.

```sh
BUNDLE=./bb10-node24-runtime-v24.22.1.tar.gz \
DEVICE_IP=169.254.0.1 \
KEY="$HOME/.ssh/bb10_rsa" \
./deploy/install-runtime.sh
```

The installer uploads the bundle, moves any existing `nodedist/` to
`nodedist.backup.<timestamp>`, extracts into
`/accounts/1000/shared/misc`, fixes modes, and runs `node -v`.

**Binary-only** (for an existing `nodedist/{bin,lib}` layout):

```sh
BINARY=./node.bin.icu2 \
DEVICE_IP=169.254.0.1 \
KEY="$HOME/.ssh/bb10_rsa" \
./deploy/install-node.sh
```

The binary-only installer copies the binary to `/tmp/node.bin.new`, backs up
`node.bin` to `node.bin.pre-icu` once, replaces it, and runs `node -v`.

If scp drops on a slow/large transfer, copy the binary over SMB to
`/accounts/1000/shared/misc/` and then `cp` it into place over SSH (the SMB
share maps to `/accounts/1000/shared`).

## 5. Verify

```sh
DEVICE_IP=169.254.0.1 KEY="$HOME/.ssh/bb10_rsa" ./deploy/verify-node.sh
```

The script checks:

```sh
node -v && npm -v && npx -v
node -e 'console.log(/\p{Emoji}/u.test("😀"), /\p{L}\p{N}/u.test("a1"))'
node -e 'const s=new Intl.Segmenter("en",{granularity:"grapheme"}); console.log([...s.segment("a👍🏽b")].map(x=>x.segment))'
node --expose-gc -e 'let k=[];for(let i=0;i<300;i++){for(let j=0;j<20000;j++)k.push({j,s:"x"+j});if(i%3===0)global.gc();k.length=0;}console.log("gc ok")'
```

For an interactive/TTY check, run `ssh -tt ... 'node -v; npm --version'`.

## 6. Rollback

Runtime-bundle install:

```sh
cd /accounts/1000/shared/misc
mv nodedist nodedist.failed
mv nodedist.backup.<timestamp> nodedist   # choose the backup from install time
```

Binary-only install:

```sh
cp -f /accounts/1000/shared/misc/nodedist/bin/node.bin.pre-icu \
      /accounts/1000/shared/misc/nodedist/bin/node.bin
chmod 755 /accounts/1000/shared/misc/nodedist/bin/node.bin
```

## 7. Notes

- qconnDoor is a userspace helper; the device does not run an SSH daemon by
  default. Keep the tunnel process alive for the whole session.
- Old SSH algorithms are required by the BB10 sshd; the scripts pass
  `HostKeyAlgorithms=+ssh-rsa`, `PubkeyAcceptedAlgorithms=+ssh-rsa`,
  `KexAlgorithms=+diffie-hellman-group1-sha1`, `Ciphers=+aes128-ctr,...`,
  `MACs=+hmac-sha1`.
- The PC's OpenSSH must allow those algorithms (OpenSSH 9.x blocks them by
  default).
