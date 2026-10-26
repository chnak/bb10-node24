#!/usr/bin/env python3
p = '/root/nodebuild/node-v24.22.1/deps/uv/src/unix/qnx.c'
s = open(p).read()
new = '''uint64_t uv_get_free_memory(void) {
  uint64_t totalmem;
  uint64_t freemem;

  get_mem_info(&totalmem, &freemem);
  return freemem;
}


uint64_t uv_get_total_memory(void) {
  uint64_t totalmem;
  uint64_t freemem;

  get_mem_info(&totalmem, &freemem);
  return totalmem;
}
'''
i = s.index('uint64_t uv_get_free_memory(void) {')
j = s.index('uint64_t uv_get_constrained_memory(void) {')
s = s[:i] + new + '\n\n' + s[j:]
open(p, 'w').write(s)
print('patched qnx.c: memory functions use get_mem_info (no popen)')
