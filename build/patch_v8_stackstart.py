#!/usr/bin/env python3
"""Fix V8's QNX stack-start computation.

QNX has no pthread_getattr_np(), and __stackavail() returns the space left
*below* the current stack pointer, so `sp + __stackavail()` points past the
top of the stack (into unmapped memory).  The GC conservative stack scanner
then walks off the stack and SIGSEGVs.

QNX maps a thread's whole stack region up front (verified on device: a 64 KB
thread stack reports all 64 KB as mapped even though < 2 KB is used), so the
top can be found by probing upwards page by page with msync(MS_ASYNC), which
returns an error as soon as the address leaves the mapping.
"""
import shutil
import sys

PATH = "/root/nodebuild/node-v24.22.1/deps/v8/src/base/platform/platform-posix.cc"

OLD = """#elif defined(V8_OS_QNX)
  // QNX has no pthread_getattr_np(). Reconstruct the stack top from the
  // current stack pointer plus the space still available below it.
  uintptr_t sp = static_cast<uintptr_t>(Stack::GetCurrentStackPosition());
  return reinterpret_cast<void*>(sp + __stackavail());
"""

NEW = """#elif defined(V8_OS_QNX)
  // QNX has no pthread_getattr_np(), and __stackavail() is the space
  // remaining *below* the current stack pointer, so sp + __stackavail()
  // points past the top of the stack and usually into unmapped memory,
  // making the conservative stack scanner crash. QNX reserves the entire
  // stack region up front, so walk up page by page and stop at the first
  // page that is no longer part of the mapping: the stack top is the end of
  // the last mapped page. Bound the walk so an unrelated mapping directly
  // above the stack cannot run away.
  constexpr uintptr_t kPageSize = 4096;
  constexpr uintptr_t kMaxStackSize = 16 * 1024 * 1024;
  uintptr_t sp =
      reinterpret_cast<uintptr_t>(Stack::GetCurrentStackPosition());
  uintptr_t page = sp & ~(kPageSize - 1);
  uintptr_t last_mapped = page;
  for (uintptr_t end = page + kMaxStackSize; page < end; page += kPageSize) {
    if (msync(reinterpret_cast<void*>(page), kPageSize, MS_ASYNC) != 0) break;
    last_mapped = page;
  }
  return reinterpret_cast<void*>(last_mapped + kPageSize);
"""


def main() -> int:
    src = open(PATH, "r", encoding="utf-8").read()
    if NEW in src:
        print("already patched")
        return 0
    if src.count(OLD) != 1:
        print("ERROR: old block not found exactly once (count=%d)" % src.count(OLD))
        return 1
    shutil.copyfile(PATH, PATH + ".pre-stackfix")
    open(PATH, "w", encoding="utf-8").write(src.replace(OLD, NEW))
    print("patched", PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
