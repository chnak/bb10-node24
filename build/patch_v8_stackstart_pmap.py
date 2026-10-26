#!/usr/bin/env python3
"""Use QNX procfs stack mappings for Stack::ObtainCurrentThreadStackStart.

The previous implementation walked upwards from the current stack pointer and
stopped at the first unmapped page. That is wrong when another mapping (heap or
another thread stack) sits directly above the current stack: the walk crosses
into it and returns a stack top megabytes too high, so the conservative GC
scanner treats heap memory as stack and hits UNREACHABLE.

QNX procfs exposes the address space via /proc/self/pmap, where every thread
stack shows up as a mapping named "{stack}" with an exact vaddr/size. Pick the
mapping containing the current stack pointer and return its end. Keep the
msync probe as a fallback if procfs is unavailable.

Anchors are scoped to the ObtainCurrentThreadStackStart function: the file has
more than one "#elif defined(V8_OS_QNX)" branch.
"""
import sys

P = "/root/nodebuild/node-v24.22.1/deps/v8/src/base/platform/platform-posix.cc"
FUNC = "Stack::StackSlot Stack::ObtainCurrentThreadStackStart() {"
QNX = "#elif defined(V8_OS_QNX)\n"
END = "#else\n  pthread_attr_t attr;"

NEW_BRANCH = '''#elif defined(V8_OS_QNX)
  // QNX has no pthread_getattr_np(), and __stackavail() is the space
  // remaining *below* the current stack pointer, so sp + __stackavail()
  // points past the top of the stack and makes the conservative stack
  // scanner crash. QNX procfs lists every thread stack as a mapping named
  // "{stack}" with an exact vaddr/size, which stays correct even when
  // another mapping is placed directly above this one (a page-by-page msync
  // probe would run into it and overshoot by megabytes).
  uintptr_t sp = static_cast<uintptr_t>(Stack::GetCurrentStackPosition());
  uintptr_t stack_top = 0;
  FILE* pmap = fopen("/proc/self/pmap", "r");
  if (pmap != nullptr) {
    char line[512];
    // Skip the "vaddr,size,flags,..." header; data lines start with "0x".
    while (fgets(line, sizeof(line), pmap) != nullptr) {
      if (line[0] != '0' || (line[1] != 'x' && line[1] != 'X')) continue;
      if (strstr(line, "{stack}") == nullptr) continue;
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
  return reinterpret_cast<void*>(last_mapped + kPageSize);
'''

src = open(P, encoding="utf-8").read()

func_idx = src.find(FUNC)
if func_idx < 0:
    print("ERROR: function not found", file=sys.stderr)
    sys.exit(1)

start_idx = src.find(QNX, func_idx)
if start_idx < 0:
    print("ERROR: QNX branch not found inside function", file=sys.stderr)
    sys.exit(1)

end_idx = src.find(END, start_idx)
if end_idx < 0:
    print("ERROR: #else/pthread_attr_t not found", file=sys.stderr)
    sys.exit(1)

src = src[:start_idx] + NEW_BRANCH + END + src[end_idx + len(END):]

if "#include <string.h>" not in src:
    src = src.replace("#include <stdio.h>\n",
                      "#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n", 1)

open(P, "w", encoding="utf-8").write(src)
print("patched ObtainCurrentThreadStackStart via /proc/self/pmap")
