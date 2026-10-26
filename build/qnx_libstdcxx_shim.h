/*
 * BB10/QNX 6.6 compatibility shim for GNU libstdc++.
 *
 * QNX's ctype.h / float.h pull in Dinkumware's <yvals.h>, which defines
 * short macros such as _C2 that collide with libstdc++ template parameter
 * names.  Include the QNX C headers first, then drop every offending macro.
 *
 * QNX 6.6's C++ headers also omit a few functions that libc does export
 * (isblank, iswblank, wcstof, wcstold), so declare them here.
 */
#ifndef BB10_QNX_LIBSTDCXX_SHIM_H
#define BB10_QNX_LIBSTDCXX_SHIM_H

#ifdef __cplusplus

#include <yvals.h>

/* C headers first: ctype.h defines the _UP/_LO/... character-class masks,
 * and <sys/siginfo.h> (reached via pthread.h) uses ::time_t. */
#include <ctype.h>
#include <wchar.h>
#include <sys/types.h>
#include <time.h>
/* V8's src/base/strings.h uses va_list without including <cstdarg>; on glibc
 * it arrives transitively, on QNX it does not. */
#include <cstdarg>

#undef _C2
#undef _CPS
#undef _C99
#undef _MAX
#undef _MIN
#undef _DOFF
#undef _FOFF
#undef _DBIAS
#undef _FBIAS
#undef _TBIAS
#undef _BITS_BYTE
#undef _MBMAX
#undef _ILONG
#undef _MEMBND
#undef _ATEXIT_T
#undef _Atexit
#undef _MAX_EXP_DIG
#undef _MAX_INT_DIG
#undef _MAX_SIG_DIG
#undef _EXFAIL
#undef _FNAMAX
#undef _FOPMAX
#undef _TNAMAX
#undef _TLS_QUAL
#undef _COMPILER_TLS
#undef _GLOBAL_LOCALE
#undef _DEFAULT_LOCFILE
#undef _FILE_OP_LOCKS
#undef _IOSTREAM_OP_LOCKS
#undef _UNINITALIZED_IS_ZERO
#undef _TERMINATION_CLEANUP
#undef _ADD_POSIX
#undef _HAS_TR1_DECLARATIONS
#undef _CPPLIB_VER

/* QNX ctype.h character-class bit macros: clash with libstdc++ identifiers
   (_UP is a typedef in unique_ptr.h).  ctype_base.h carries the numbers. */
#undef _XB
#undef _XA
#undef _XS
#undef _BB
#undef _CN
#undef _DI
#undef _LO
#undef _PU
#undef _SP
#undef _UP
#undef _XD

/* ctype.h turns isblank/iswblank into macros; drop them so the real
   libc functions can be declared for libstdc++. */
#ifdef isblank
#undef isblank
#endif
#ifdef iswblank
#undef iswblank
#endif
extern "C" int isblank(int);
extern "C" int iswblank(wint_t);

/* Present in libc.so.3 but only declared in C mode by QNX's headers. */
extern "C" float wcstof(const wchar_t *, wchar_t **);
extern "C" long double wcstold(const wchar_t *, wchar_t **);

/* QNX signal.h marks SA_ONSTACK as "not supported yet" and leaves it
 * undefined; V8 sets it unconditionally in its sampler and stack-trace code. */
#include <signal.h>
#ifndef SA_ONSTACK
#define SA_ONSTACK 0
#endif

#endif /* __cplusplus */
#endif /* BB10_QNX_LIBSTDCXX_SHIM_H */
