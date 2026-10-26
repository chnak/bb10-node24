#!/usr/bin/env python3
# libuv/QNX: struct dirent::d_name is a flexible array, so sizeof(*dent)
# copies only the header and none of the name.  Copy d_namelen+1 bytes.
p = '/root/nodebuild/node-v24.22.1/deps/uv/src/unix/fs.c'
s = open(p).read()

old_decl = '''  uv__dirent_t** dents;
  uv__dirent_t* dent;
  struct dirent* ent;
  DIR* dir;
  size_t n;
  size_t allocated;
'''
new_decl = '''  uv__dirent_t** dents;
  uv__dirent_t* dent;
  struct dirent* ent;
  DIR* dir;
  size_t n;
  size_t allocated;
  size_t ent_size;
'''
assert s.count(old_decl) == 1
s = s.replace(old_decl, new_decl)

old_malloc = '''    dent = uv__malloc(sizeof(*dent));
'''
new_malloc = '''    /* QNX struct dirent ends in a flexible array: size the copy by name. */
    ent_size = offsetof(uv__dirent_t, d_name) +
               (ent->d_namelen ? (size_t) ent->d_namelen
                               : strlen(ent->d_name)) + 1;
    dent = uv__malloc(ent_size);
'''
assert s.count(old_malloc) == 1
s = s.replace(old_malloc, new_malloc)

old_copy = '''    memcpy(dent, ent, sizeof(*dent));
'''
new_copy = '''    memcpy(dent, ent, ent_size);
    dent->d_name[ent_size - offsetof(uv__dirent_t, d_name) - 1] = '\\0';
'''
assert s.count(old_copy) == 1
s = s.replace(old_copy, new_copy)

open(p, 'w').write(s)
print('patched libuv fs.c: dirent flexible-array copy')
