# ICU build (small-icu + break iteration)

This document covers the ICU-enabled build (`node-v24.22.1-icu`). The
non-ICU build and the general QNX workarounds are described in
[`BUILD.md`](BUILD.md).

## Why

Node's stock `small-icu` build trims the ICU data down to English/root and, in
`tools/icu/icu_small.json`, sets `brkitr`, `brkfiles` and `brkdict` to
`none`. As a result `icu::BreakIterator::create*Instance()` returns `null` and
V8 (release build, no null check) crashes in `JSSegments::Create` when
`Intl.Segmenter` is used:

```
Memory fault (core dumped)
... JSSegments::Create ... js-segments.cc
```

Other Intl APIs (`NumberFormat`, `DateTimeFormat`, `Collator`, `PluralRules`,
`ListFormat`) work with stock small-icu; only segmentation needs the break
data.

## Configure

```bash
cd /root/nodebuild/node-v24.22.1-icu
./configure \
  --dest-os=qnx --dest-cpu=arm --cross-compiling \
  --shared-libuv \
  --shared-libuv-includes=/root/nodebuild/uv-qnx/include \
  --shared-libuv-libpath=/root/nodebuild/uv-qnx/lib \
  --with-intl=small-icu --with-arm-fpu=vfpv3 \
  --without-inspector --without-node-snapshot --openssl-no-asm
```

If you re-run `./configure`, re-apply `build/patch_host_mk.py` afterwards
(see section 5.7 of `BUILD.md`).

## Keep the break data

`patches/qnx-bb10-node24.patch` already contains this change (it is the diff
of `tools/icu/icu_small.json` against upstream). If you patch the tree by
hand instead, copy [`../patches/icu_small.json`](../patches/icu_small.json)
over `tools/icu/icu_small.json` before building:

```bash
cp ../patches/icu_small.json tools/icu/icu_small.json
```

The important changes are:

```json
"brkitr":    "leavealone",
"brkfiles":  "leavealone",
"brkdict":   "leavealone"
```

and `"brkitr/root.res"` is removed from the `remove` list.

**All three are required.** `brkitr/root.res` depends on the break
dictionaries; if `brkdict` is trimmed, `icupkg` reports the missing dependency
and cascades the removal of the whole `brkitr` tree (the build still succeeds,
but `Intl.Segmenter` crashes again).

The resulting embedded data is about 7.7 MB (vs 4.7 MB stock), and the
stripped binary grows by ~3.8 MB.

## Patch scripts and the ICU tree path

The scripts under `../build/` default to the non-ICU tree
`/root/nodebuild/node-v24.22.1`. When working in the ICU tree
(`node-v24.22.1-icu`), point them at it first:

```bash
sed -i 's#node-v24.22.1#node-v24.22.1-icu#g' ../build/patch_*.py
```

## Build

```bash
make -j3 BUILDTYPE=Release node
llvm-strip-18 --strip-all out/Release/node
```

Copy the stripped binary to the device; see
[`DEVICE-DEPLOY.md`](DEVICE-DEPLOY.md).

## Verify

```sh
node -v
node -e 'console.log(/\p{Emoji}/u.test("😀"), /\p{L}\p{N}/u.test("a1"))'
node -e 'const s=new Intl.Segmenter("en",{granularity:"grapheme"}); console.log([...s.segment("a👍🏽b")].map(x=>x.segment))'
node -e 'const s=new Intl.Segmenter("en",{granularity:"word"}); console.log([...s.segment("hello world")].map(x=>x.segment))'
```

Expected: `true true`, `["a","👍🏽","b"]`, `["hello"," ","world"]`.

## Other patches used by this build

The stack, Maglev and libuv fixes are the same as in the non-ICU build; see
`BUILD.md` sections 5.1–5.8 and the scripts under `../build/`. In particular:

- `patch_v8_stackstart_pmap.py` — V8 stack top from `/proc/self/pmap`
- `patch_final.py` — Maglev off by default + final stack branch
- `patch_uv_ptsname_qnx.py` — avoid `ptsname()` (not exported by QNX libc)
- `patch_uv_core_qnx.py` — `fcntl()` return-value fix
- `patch_host_mk.py` — remove `-luv` from x86-32 host tool link lines
- `patch_json_scalar.py` — Highway 32-bit host compile fix
