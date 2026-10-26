#!/usr/bin/env python3
"""Avoid the ptsname() reference in libuv on QNX.

QNX libc declares ptsname() in <stdlib.h> but does not export it, so the
dynamic loader reports:

    ldd:FATAL: Unresolved symbol "ptsname" called from libuv.so.1

uv__tty_is_slave() only uses ptsname() as a fallback (non-Linux/BSD/macOS
branch). Returning "is a slave" is correct for standard streams and avoids the
unresolved symbol entirely.
"""
import sys

P = "/root/nodebuild/node-v24.22.1/deps/uv/src/unix/tty.c"
MARK = "QNX libc does not provide ptsname()"

src = open(P, encoding="utf-8").read()
if MARK in src:
    print("already patched")
    sys.exit(0)

old = """#else
  /* Fallback to ptsname
   */
  result = ptsname(fd) == NULL;
#endif"""
new = """#elif defined(__QNX__)
  /* QNX libc does not provide ptsname() (declared in <stdlib.h> but not
     exported), so calling it leaves an unresolved dynamic symbol. The
     process's standard streams are slave terminals; treat every tty as a
     slave. */
  (void) fd;
  result = 1;
#else
  /* Fallback to ptsname
   */
  result = ptsname(fd) == NULL;
#endif"""

if old not in src:
    print("ERROR: anchor not found", file=sys.stderr)
    sys.exit(1)

src = src.replace(old, new, 1)
open(P, "w", encoding="utf-8").write(src)
print("patched", P)
