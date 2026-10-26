#!/usr/bin/env python3
# QNX 6.6 stdlib.h declares __cxa_atexit() without an exception spec.
# GCC 13's cxxabi.h redeclares it _GLIBCXX_NOTHROW (noexcept), which clang
# rejects as an exception-specification mismatch.  Drop the spec there.
p = '/opt/gcc13qnx/include/c++/13/cxxabi.h'
s = open(p).read()
marker = '__cxa_atexit(void (*)(void*), void*, void*) _GLIBCXX_NOTHROW;'
if marker not in s and '__cxa_atexit(void (*)(void*), void*, void*);' in s:
    print('already patched:', p)
    raise SystemExit(0)
old = '''#ifdef _GLIBCXX_CDTOR_CALLABI
  __cxa_atexit(void (_GLIBCXX_CDTOR_CALLABI *)(void*), void*, void*) _GLIBCXX_NOTHROW;
#else
  __cxa_atexit(void (*)(void*), void*, void*) _GLIBCXX_NOTHROW;
#endif'''
new = '''#ifdef _GLIBCXX_CDTOR_CALLABI
  __cxa_atexit(void (_GLIBCXX_CDTOR_CALLABI *)(void*), void*, void*);
#else
  __cxa_atexit(void (*)(void*), void*, void*);
#endif'''
assert old in s, p
open(p, 'w').write(s.replace(old, new))
print('patched cxxabi.h __cxa_atexit exception spec')
