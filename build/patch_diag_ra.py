#!/usr/bin/env python3
"""Diagnostics: print the caller of V8_Fatal, and the computed stack top.

Both insertions are idempotent (guarded by marker strings). Remove later by
restoring from the .pre-stackfix backup and re-applying the pmap patch.
"""
import sys

V = "/root/nodebuild/node-v24.22.1/deps/v8"

# 1) V8_Fatal: print return address of the UNREACHABLE/FATAL call site.
log = V + "/src/base/logging.cc"
src = open(log, encoding="utf-8").read()
if "[v8fatal-ra]" in src:
    print("logging.cc already instrumented")
else:
    anchor = "  va_list arguments;\n  va_start(arguments, format);"
    repl = ("  fprintf(stderr, \"[v8fatal-ra] ra0=%p ra1=%p\\n\",\n"
            "          __builtin_return_address(0),\n"
            "          __builtin_return_address(1));\n"
            + anchor)
    if anchor not in src:
        print("ERROR: logging.cc anchor not found", file=sys.stderr)
        sys.exit(1)
    src = src.replace(anchor, repl, 1)
    open(log, "w", encoding="utf-8").write(src)
    print("instrumented logging.cc")

# 2) pmap branch: print sp and the derived stack top.
posix = V + "/src/base/platform/platform-posix.cc"
src = open(posix, encoding="utf-8").read()
if "[qnx-stack-pmap]" in src:
    print("platform-posix.cc already instrumented")
else:
    anchor = ("  if (stack_top > sp) {\n"
              "    return reinterpret_cast<void*>(stack_top);\n"
              "  }")
    repl = ("  if (stack_top > sp) {\n"
            "    fprintf(stderr,\n"
            "            \"[qnx-stack-pmap] sp=%p top=%p delta=%ld\\n\",\n"
            "            reinterpret_cast<void*>(sp),\n"
            "            reinterpret_cast<void*>(stack_top),\n"
            "            static_cast<long>(stack_top - sp));\n"
            "    return reinterpret_cast<void*>(stack_top);\n"
            "  }\n"
            "  fprintf(stderr, \"[qnx-stack-pmap] NO MAP for sp=%p\\n\",\n"
            "          reinterpret_cast<void*>(sp));")
    if anchor not in src:
        print("ERROR: platform-posix.cc anchor not found", file=sys.stderr)
        sys.exit(1)
    src = src.replace(anchor, repl, 1)
    open(posix, "w", encoding="utf-8").write(src)
    print("instrumented platform-posix.cc")
