#!/usr/bin/env python3
"""Node core (not deps) fixes for QNX 6.6.

- QNX netdb.h has no AI_ADDRCONFIG; define it to 0 like AI_ALL/AI_V4MAPPED
  above it, so the constant exists for JS but adds no flags.
- QNX has no <execinfo.h>/backtrace(), so HAVE_EXECINFO_H must be 0.
"""
import sys

N = "/root/nodebuild/node-v24.22.1"

# --- src/cares_wrap.cc -------------------------------------------------------
p = N + "/src/cares_wrap.cc"
s = open(p, encoding="utf-8").read()
old = """#ifndef AI_V4MAPPED
# define AI_V4MAPPED 0
#endif
"""
new = old + """#ifndef AI_ADDRCONFIG
# define AI_ADDRCONFIG 0
#endif
"""
if "# define AI_ADDRCONFIG 0" not in s:
    assert s.count(old) == 1, "AI_V4MAPPED anchor not unique"
    s = s.replace(old, new)
    open(p, "w", encoding="utf-8").write(s)
    print("cares_wrap.cc patched")
else:
    print("cares_wrap.cc already patched")

# --- src/debug_utils.cc ------------------------------------------------------
p = N + "/src/debug_utils.cc"
s = open(p, encoding="utf-8").read()
old = """#if defined(__linux__) && !defined(__GLIBC__) || \\
    defined(__UCLIBC__) || \\
    defined(_AIX)
#define HAVE_EXECINFO_H 0
"""
new = """#if defined(__linux__) && !defined(__GLIBC__) || \\
    defined(__UCLIBC__) || \\
    defined(_AIX) || defined(__QNX__)
#define HAVE_EXECINFO_H 0
"""
if "defined(__QNX__)\n#define HAVE_EXECINFO_H 0" in s:
    print("debug_utils.cc already patched")
else:
    assert s.count(old) == 1, "HAVE_EXECINFO_H anchor not unique"
    s = s.replace(old, new)
    open(p, "w", encoding="utf-8").write(s)
    print("debug_utils.cc patched")
