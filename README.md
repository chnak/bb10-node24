# Node.js 24 for BlackBerry 10 / QNX 6.6

A cross-compiled **Node.js v24.22.1** build for BlackBerry 10 devices
(QNX 6.6, 32-bit ARMv7 `armle-v7`), including npm 11.19.1.

The build is patched for the quirks of QNX and BB10: V8 stack detection via
`/proc/self/pmap`, Maglev disabled (its code generation miscompiles on this
toolchain), libuv `fcntl`/`ptsname`/`dirent` fixes, and a small-ICU data set
that keeps the break-iteration data so `Intl.Segmenter` works.

> Chinese build notes are in [`docs/BUILD.md`](docs/BUILD.md) and
> [`docs/ICU-BUILD.md`](docs/ICU-BUILD.md). Deployment notes are in
> [`docs/DEVICE-DEPLOY.md`](docs/DEVICE-DEPLOY.md).

## Download

Prebuilt binaries are published on the
[Releases](https://github.com/chnak/bb10-node24/releases) page.

| Asset | Size | SHA-256 |
|---|---|---|
| `bb10-node24-runtime-v24.22.1.tar.gz` **（推荐 / recommended）** | 28,447,631 B | `451291df7441cb9bd44dfc2f7004f6b974c79153cfb7bfbc7c3fcf462a5589a4` |
| `node.bin.icu2`（仅二进制 / binary only） | 62,725,912 B | `9a0b965e33769cb409b8dfb7f46c32c78d897b88a79d63aa312605ceff50968b` |

The **runtime bundle** is the recommended download. It contains
`bin/node.bin`, relocatable `node`/`npm`/`npx` wrappers, the patched
`libuv.so.1`, `libstdc++.so.6`, `libgcc_s.so.1`, `libbacktrace.so.1`, and
npm 11.19.1. Extract it into `/accounts/1000/shared/misc` so it creates
`nodedist/`.

The standalone `node.bin.icu2` requires an existing
`/accounts/1000/shared/misc/nodedist/{bin,lib}` layout with the patched
libraries and npm.

## Features

- Node.js **v24.22.1**, npm/npx **11.19.1**
- `--with-intl=small-icu` with **break-iteration data kept** (`brkitr`), so
  `Intl.Segmenter` works natively (Stock Node small-icu strips it and V8 then
  crashes on `segment()`.)
- V8 stack-top detection uses `/proc/self/pmap` (QNX has no `/proc/self/maps`)
- Maglev disabled by default (`--maglev` still available for debugging)
- libuv: `fcntl()` return value, `ptsname()`, `dirent.d_name` fixes
- Verified on Z30/Q20-class hardware: node/npm/npx, TTY, GC stress,
  Unicode property escapes, `Intl.Segmenter`, and common Node CLI tools.

## Repository layout

```
docs/       build notes and device deployment guide
build/      cross-toolchain wrapper, prep scripts and source patch scripts
patches/    drop-in data patches (ICU small-data config, minimal uchar.h)
deploy/     device connect/install/verify scripts (placeholders, no secrets)
licenses/   Node.js and ICU license texts
```

## Build

Requirements:

- WSL/Ubuntu with clang-18, lld-18, llvm-18, dpkg-deb, curl, python3
- BlackBerry 10 NDK 10.3.1.995 at `/opt/bb10ndk/target_10_3_1_995`
- Node.js v24.22.1 source tree at `/root/nodebuild/node-v24.22.1-icu`

The full field notes, including every workaround, are in
[`docs/BUILD.md`](docs/BUILD.md). For the ICU build specifically see
[`docs/ICU-BUILD.md`](docs/ICU-BUILD.md).

Key steps (from a configured tree):

```bash
cd /root/nodebuild/node-v24.22.1-icu
./configure \
  --dest-os=qnx --dest-cpu=arm --cross-compiling \
  --shared-libuv \
  --shared-libuv-includes=/root/nodebuild/uv-qnx/include \
  --shared-libuv-libpath=/root/nodebuild/uv-qnx/lib \
  --with-intl=small-icu --with-arm-fpu=vfpv3 \
  --without-inspector --without-node-snapshot --openssl-no-asm

# after configure, apply the host-link and source patches from build/
# and copy patches/icu_small.json over tools/icu/icu_small.json

make -j3 BUILDTYPE=Release node
llvm-strip-18 --strip-all out/Release/node
```

## Deploy to a BB10 device

1. Enable **Development Mode** on the device (Settings → Security and Privacy →
   Development Mode).
2. Start the qconnDoor tunnel:

   ```sh
   DEVICE_IP=169.254.0.1 DEVICE_PASSWORD='<device password>' \
     KEY="$HOME/.ssh/bb10_rsa" ./deploy/connect.sh
   ```

   The tunnel process must stay running; SSH is only available while it is up.
3. Install the complete runtime (recommended):

   ```sh
   BUNDLE=./bb10-node24-runtime-v24.22.1.tar.gz \
   DEVICE_IP=169.254.0.1 KEY="$HOME/.ssh/bb10_rsa" \
     ./deploy/install-runtime.sh
   ```

   This extracts `nodedist/` (node, npm, patched libuv and C++ runtime) and
   moves any previous runtime to `nodedist.backup.<timestamp>`.

   Binary-only alternative (for an existing layout):

   ```sh
   BINARY=./node.bin.icu2 DEVICE_IP=169.254.0.1 KEY="$HOME/.ssh/bb10_rsa" \
     ./deploy/install-node.sh
   ```
4. Verify:

   ```sh
   DEVICE_IP=169.254.0.1 KEY="$HOME/.ssh/bb10_rsa" ./deploy/verify-node.sh
   ```

See [`docs/DEVICE-DEPLOY.md`](docs/DEVICE-DEPLOY.md) for the backup/rollback
layout and the SMB fallback when USB/SSH is unavailable.

## Known limitations

- The build targets `armle-v7` and QNX 6.6; it is not compatible with 64-bit
  QNX builds.
- Maglev stays off by default. `--maglev` can crash; do not enable it in
  production.
- `small-icu` includes only English/root locale data. The `brkitr` data is
  kept so `Intl.Segmenter` works; other locale data is not bundled.
- No official Node.js support for QNX is implied; this is a community port.

## License

MIT (see [`LICENSE`](LICENSE)). Node.js and ICU license texts are included in
[`licenses/`](licenses/). Node.js is © the Node.js contributors; ICU is
© Unicode, Inc. and others.

## 中文简介

这是给 BlackBerry 10（QNX 6.6 / ARMv7）交叉编译的 Node.js 24.22.1，包含
npm 11.19.1。仓库里有完整构建记录、补丁脚本和设备部署脚本；预编译二进制在
Releases 页面。详细构建步骤见 `docs/BUILD.md`，ICU/Intl 修复见
`docs/ICU-BUILD.md`，部署见 `docs/DEVICE-DEPLOY.md`。
