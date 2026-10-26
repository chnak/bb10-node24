#!/usr/bin/env python3
"""Skip V8's Highway SIMD JSON path when Highway targets scalar only.

On x86-32 the host compiler is built without -msse2, so Highway selects
HWY_SCALAR (1 lane). json-stringifier.cc instantiates FixedTag<SrcChar, 16>,
which requires >= 16 lanes and fails to compile. Guard the SIMD call with
HWY_TARGET != HWY_SCALAR; SSE2/NEON builds keep the fast path, scalar builds
use the existing SWAR fallback.
"""
import sys

PATHS = [
    "/root/nodebuild/node-v24.22.1-icu/deps/v8/src/json/json-stringifier.cc",
    "/root/nodebuild/node-v24.22.1/deps/v8/src/json/json-stringifier.cc",
]

OLD = """  constexpr int kUseSimdLengthThreshold = 32;
  if (length >= kUseSimdLengthThreshold) {
    return AppendStringSIMD(chars, length, no_gc);
  }
  return AppendStringSWAR(chars, length, 0, 0, no_gc);"""

NEW = """  constexpr int kUseSimdLengthThreshold = 32;
#if HWY_TARGET != HWY_SCALAR
  if (length >= kUseSimdLengthThreshold) {
    return AppendStringSIMD(chars, length, no_gc);
  }
#endif
  return AppendStringSWAR(chars, length, 0, 0, no_gc);"""

for path in PATHS:
    try:
        src = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        print("missing:", path)
        continue
    if "HWY_TARGET != HWY_SCALAR" in src:
        print("already patched:", path)
        continue
    if OLD not in src:
        print("ERROR: anchor not found in", path, file=sys.stderr)
        continue
    open(path, "w", encoding="utf-8").write(src.replace(OLD, NEW, 1))
    print("patched:", path)
