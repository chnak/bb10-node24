#!/usr/bin/env python3
"""Second round of QNX patches for V8's platform-posix.cc.

QNX 6.6 provides posix_madvise() but not madvise(), and has no
pthread_getattr_np().  Both are used unconditionally by platform-posix.cc.
"""
import sys

P = "/root/nodebuild/node-v24.22.1/deps/v8/src/base/platform/platform-posix.cc"

with open(P, "r", encoding="utf-8") as f:
    src = f.read()

orig = src

# 1) <alloca.h> for __stackavail()
old = "#include <unistd.h>\n"
new = "#include <unistd.h>\n#if V8_OS_QNX\n#include <alloca.h>  // for __stackavail\n#endif\n"
if "__stackavail" not in src:
    assert src.count(old) == 1, "unistd include anchor not unique"
    src = src.replace(old, new)
else:
    print("alloca.h include already present")

# 2) OS::DiscardSystemPages: QNX has posix_madvise() only.
old = """#else
  int ret = madvise(address, size, MADV_DONTNEED);
#endif
  // madvise with MADV_DONTNEED only fails on illegal parameters. That's a bug
"""
new = """#elif defined(V8_OS_QNX)
  // QNX has no madvise(); posix_madvise() returns an error number directly.
  int ret = posix_madvise(address, size, POSIX_MADV_DONTNEED);
#else
  int ret = madvise(address, size, MADV_DONTNEED);
#endif
  // madvise with MADV_DONTNEED only fails on illegal parameters. That's a bug
"""
if "POSIX_MADV_DONTNEED" not in src:
    assert src.count(old) == 1, "DiscardSystemPages anchor not unique"
    src = src.replace(old, new)

# 3) Stack::ObtainCurrentThreadStackStart: synthesize stack top on QNX.
old = """#else
  pthread_attr_t attr;
  int error = pthread_getattr_np(pthread_self(), &attr);
"""
new = """#elif defined(V8_OS_QNX)
  // QNX has no pthread_getattr_np(). Reconstruct the stack top from the
  // current stack pointer plus the space still available below it.
  uintptr_t sp = static_cast<uintptr_t>(Stack::GetCurrentStackPosition());
  return reinterpret_cast<void*>(sp + __stackavail());
#else
  pthread_attr_t attr;
  int error = pthread_getattr_np(pthread_self(), &attr);
"""
if "__stackavail()" not in src:
    assert src.count(old) == 1, "ObtainCurrentThreadStackStart anchor not unique"
    src = src.replace(old, new)

if src == orig:
    print("NO CHANGES (already patched)")
else:
    with open(P, "w", encoding="utf-8") as f:
        f.write(src)
    print("platform-posix.cc patched")
