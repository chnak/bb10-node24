#!/usr/bin/env python3
# V8 base fixes for QNX 6.6:
#  - no malloc_usable_size()
#  - no <sys/syscall.h>
#  - no SA_ONSTACK (QNX signal.h marks it unsupported)
import sys

V = '/root/nodebuild/node-v24.22.1/deps/v8'
changed = False

def patch(path, old, new, marker):
    global changed
    p = V + path
    s = open(p).read()
    if marker in s:
        print('already patched:', path)
        return
    if old not in s:
        print('PATTERN NOT FOUND:', path)
        sys.exit(1)
    open(p, 'w').write(s.replace(old, new, 1))
    print('patched:', path)
    changed = True

patch('/src/base/platform/memory.h',
      '#if (V8_OS_POSIX && !V8_OS_AIX && !V8_OS_SOLARIS && !V8_OS_ZOS && !V8_OS_OPENBSD) || V8_OS_WIN',
      '#if (V8_OS_POSIX && !V8_OS_AIX && !V8_OS_SOLARIS && !V8_OS_ZOS && !V8_OS_OPENBSD && !V8_OS_QNX) || V8_OS_WIN',
      '!V8_OS_OPENBSD && !V8_OS_QNX')

patch('/src/base/platform/platform-posix.cc',
      '#if !defined(_AIX) && !defined(V8_OS_FUCHSIA) && !V8_OS_ZOS\n#include <sys/syscall.h>\n#endif',
      '#if !defined(_AIX) && !defined(V8_OS_FUCHSIA) && !V8_OS_ZOS && !defined(V8_OS_QNX)\n#include <sys/syscall.h>\n#endif',
      '!V8_OS_ZOS && !defined(V8_OS_QNX)')

patch('/src/base/debug/stack_trace_posix.cc',
      'bool EnableInProcessStackDumping() {',
      '#if defined(V8_OS_QNX) && !defined(SA_ONSTACK)\n'
      '// QNX signal.h marks SA_ONSTACK as "not supported yet".\n'
      '#define SA_ONSTACK 0\n'
      '#endif\n\n'
      'bool EnableInProcessStackDumping() {',
      'QNX signal.h marks SA_ONSTACK')

print('done' if changed else 'nothing to do')
