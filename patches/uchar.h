#ifndef _UCHAR_H_INCLUDED
#define _UCHAR_H_INCLUDED
/* Minimal C11 <uchar.h> for QNX 6.6 / BB10 NDK.
   Provides the character types required by C11; the mbstate conversion
   functions are not declared because ICU does not use them here. */
#include <stdint.h>
#ifndef __cplusplus
typedef uint16_t char16_t;
typedef uint32_t char32_t;
#endif
#endif /* _UCHAR_H_INCLUDED */
