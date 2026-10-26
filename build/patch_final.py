#!/usr/bin/env python3
"""Final source changes for the QNX build:

1. Default Maglev off (it hits UNREACHABLE in Uint32Mod on ARM/QNX). The
   runtime --maglev flag still works for opt-in testing.
2. Remove the V8_Fatal return-address diagnostic.
3. Replace the QNX stack-start branch with pmap lookup + msync fallback,
   with diagnostics gated behind QNX_STACK_DEBUG.
"""
import sys

V = "/root/nodebuild/node-v24.22.1/deps/v8"

# ---- 1. Maglev default off -------------------------------------------------
p = V + "/src/flags/flag-definitions.h"
src = open(p, encoding="utf-8").read()
old = 'DEFINE_BOOL(maglev, true, "enable the maglev optimizing compiler")'
new = ('// Maglev on ARM/QNX hits UNREACHABLE in Uint32Mod: acquiring a VFP\n'
       '// scratch register fails in UseScratchRegisterScope::AcquireVfp.\n'
       '// Keep it available via --maglev but off by default.\n'
       'DEFINE_BOOL(maglev, false, "enable the maglev optimizing compiler")')
if new in src:
    print("flag-definitions.h already patched")
elif old in src:
    src = src.replace(old, new, 1)
    open(p, "w", encoding="utf-8").write(src)
    print("patched flag-definitions.h (maglev default off)")
else:
    print("ERROR: maglev flag line not found", file=sys.stderr)
    sys.exit(1)

# ---- 2. remove V8_Fatal diagnostic ----------------------------------------
p = V + "/src/base/logging.cc"
src = open(p, encoding="utf-8").read()
diag = ('  fprintf(stderr, "[v8fatal-ra] ra0=%p ra1=%p\\n",\n'
        '          __builtin_return_address(0),\n'
        '          __builtin_return_address(1));\n')
if diag in src:
    src = src.replace(diag, "", 1)
    open(p, "w", encoding="utf-8").write(src)
    print("removed logging.cc diagnostic")
else:
    print("logging.cc diagnostic not present")

# ---- 3. final QNX stack-start branch --------------------------------------
P = V + "/src/base/platform/platform-posix.cc"
FUNC = "Stack::StackSlot Stack::ObtainCurrentThreadStackStart() {"
QNX = "#elif defined(V8_OS_QNX)\n"
END = "#else\n  pthread_attr_t attr;"

BRANCH = '''#elif defined(V8_OS_QNX)
  // QNX has no pthread_getattr_np(), and __stackavail() is the space
  // remaining *below* the current stack pointer, so sp + __stackavail()
  // points past the top of the stack. QNX procfs lists thread stacks as
  // mappings named "{stack}" with an exact vaddr/size; prefer that, since a
  // page-by-page msync probe can run into an adjacent mapping and overshoot.
  uintptr_t sp = static_cast<uintptr_t>(Stack::GetCurrentStackPosition());
  uintptr_t stack_top = 0;
  int stack_lines = 0;
  FILE* pmap = fopen("/proc/self/pmap", "r");
  if (pmap != nullptr) {
    char line[512];
    // Skip the "vaddr,size,flags,..." header; data lines start with "0x".
    while (fgets(line, sizeof(line), pmap) != nullptr) {
      if (line[0] != '0' || (line[1] != 'x' && line[1] != 'X')) continue;
      if (strstr(line, "{stack}") == nullptr) continue;
      ++stack_lines;
      char* end = nullptr;
      uintptr_t vaddr = strtoull(line, &end, 16);
      if (end == nullptr || *end != ',') continue;
      uintptr_t size = strtoull(end + 1, &end, 16);
      if (size != 0 && vaddr <= sp && sp - vaddr < size) {
        stack_top = vaddr + size;
        break;
      }
    }
    fclose(pmap);
  }
  if (stack_top > sp) {
    if (getenv("QNX_STACK_DEBUG") != nullptr) {
      fprintf(stderr, "[qnx-stack] pmap sp=%p top=%p stack_lines=%d\\n",
              reinterpret_cast<void*>(sp),
              reinterpret_cast<void*>(stack_top), stack_lines);
    }
    return reinterpret_cast<void*>(stack_top);
  }

  // Fallback: walk up page by page and stop at the first unmapped page.
  // Bound the walk so an unrelated mapping directly above the stack cannot
  // run away.
  constexpr uintptr_t kPageSize = 4096;
  constexpr uintptr_t kMaxStackSize = 16 * 1024 * 1024;
  uintptr_t page = sp & ~(kPageSize - 1);
  uintptr_t last_mapped = page;
  for (uintptr_t end = page + kMaxStackSize; page < end; page += kPageSize) {
    if (msync(reinterpret_cast<void*>(page), kPageSize, MS_ASYNC) != 0) break;
    last_mapped = page;
  }
  if (getenv("QNX_STACK_DEBUG") != nullptr) {
    fprintf(stderr, "[qnx-stack] fallback sp=%p top=%p stack_lines=%d\\n",
            reinterpret_cast<void*>(sp),
            reinterpret_cast<void*>(last_mapped + kPageSize), stack_lines);
  }
  return reinterpret_cast<void*>(last_mapped + kPageSize);
'''

src = open(P, encoding="utf-8").read()
fi = src.find(FUNC)
if fi < 0:
    print("ERROR: function not found", file=sys.stderr)
    sys.exit(1)
si = src.find(QNX, fi)
if si < 0:
    print("ERROR: QNX branch not found", file=sys.stderr)
    sys.exit(1)
ei = src.find(END, si)
if ei < 0:
    print("ERROR: branch end not found", file=sys.stderr)
    sys.exit(1)
src = src[:si] + BRANCH + END + src[ei + len(END):]

if "#include <string.h>" not in src:
    src = src.replace("#include <stdio.h>\n",
                      "#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n", 1)

open(P, "w", encoding="utf-8").write(src)
print("wrote final QNX stack-start branch")
