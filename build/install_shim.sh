#!/bin/bash
set -e
mkdir -p /root/nodebuild/qnxshim
cat > /root/nodebuild/qnxshim/shim.cc <<'EOF'
// Runtime shims for Node.js on QNX 6.6/BB10.
//
// The build uses GCC 13 C++ headers (Node 24 needs C++20 library support),
// but the only libstdc++ available on the target is GCC 9.3.  These are the
// GCC 11+ runtime entry points the headers reference but GCC 9.3 lacks.

#include <cstddef>
#include <cstring>
#include <mutex>
#include <new>
#include <pthread.h>
#include <string>

// std::call_once support: GCC 13's <mutex> uses these thread-local globals
// plus __once_proxy.  Emulated TLS (libgcc __emutls_get_address) backs the
// __thread variables, matching how QNX's own toolchain builds.
namespace std {
__thread void* __once_callable = nullptr;
__thread void (*__once_call)() = nullptr;
}  // namespace std

extern "C" void __once_proxy(void) {
  if (std::__once_call != nullptr) std::__once_call();
}

namespace std {
// GCC 11+ entry point used by the allocator on length overflow.
void __throw_bad_array_new_length() { throw std::bad_array_new_length(); }
}  // namespace std

// Instantiate the out-of-line basic_string helper that GCC 13's headers
// declare with an extern template but GCC 9.3's library does not define.
template void std::basic_string<char>::_M_replace_cold(char*, std::size_t,
                                                       const char*, std::size_t,
                                                       std::size_t);

// libatomic replacement: QNX has no libatomic, and these are the generic
// entry points the compiler emits for operations it cannot inline.
namespace {
pthread_mutex_t g_atomic_lock = PTHREAD_MUTEX_INITIALIZER;
}  // namespace

// clang treats these names as builtins and rejects redeclaring them, so the
// definitions carry an asm label instead.
extern "C" bool shim_atomic_is_lock_free(std::size_t, const void*)
    asm("__atomic_is_lock_free");
extern "C" bool shim_atomic_compare_exchange(std::size_t, void*, void*, void*,
                                             int, int)
    asm("__atomic_compare_exchange");

extern "C" bool shim_atomic_is_lock_free(std::size_t size, const void*) {
  return size <= sizeof(void*);
}

extern "C" bool shim_atomic_compare_exchange(std::size_t size, void* ptr,
                                             void* expected, void* desired,
                                             int /*success_memorder*/,
                                             int /*failure_memorder*/) {
  pthread_mutex_lock(&g_atomic_lock);
  bool equal = std::memcmp(ptr, expected, size) == 0;
  if (equal) {
    std::memcpy(ptr, desired, size);
  } else {
    std::memcpy(expected, ptr, size);
  }
  pthread_mutex_unlock(&g_atomic_lock);
  return equal;
}
EOF

cd /root/nodebuild/qnxshim
/root/nodebuild/toolchain/qnx-clang++ -femulated-tls -O2 -c shim.cc -o shim.o
echo "=== shim symbols ==="
nm shim.o | grep -E '__once|_M_replace_cold|__throw_bad_array|__atomic|__emutls' | head -20
