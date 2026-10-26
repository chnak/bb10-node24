#!/bin/bash
set -u
S=/opt/bb10ndk/target_10_3_1_995/qnx6
cat > "$S/usr/include/uchar.h" <<'HDR'
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
HDR
ls -l "$S/usr/include/uchar.h"
echo "== test =="
echo '#include <uchar.h>
int main(void){char16_t c=0;return (int)c;}' > /tmp/t_uchar.c
/root/nodebuild/toolchain/qnx-clang -c /tmp/t_uchar.c -o /tmp/t_uchar.o && echo COMPILE_OK
