#!/usr/bin/env python3
# libuv: QNX 6.6 libc has no scandir(); emulate it inside uv__fs_scandir.
p = '/root/nodebuild/node-v24.22.1/deps/uv/src/unix/fs.c'
s = open(p).read()

old = '''static ssize_t uv__fs_scandir(uv_fs_t* req) {
  uv__dirent_t** dents;
  int n;

  dents = NULL;
  n = scandir(req->path, &dents, uv__fs_scandir_filter,
              (int (*)(const void*, const void*)) uv__fs_scandir_sort);
'''
new = '''static ssize_t uv__fs_scandir(uv_fs_t* req) {
#if defined(__QNX__)
  /* QNX 6.6 libc does not export scandir(); emulate it. */
  uv__dirent_t** dents;
  uv__dirent_t* dent;
  struct dirent* ent;
  DIR* dir;
  size_t n;
  size_t allocated;

  dents = NULL;
  n = 0;
  allocated = 0;
  dir = opendir(req->path);
  if (dir == NULL)
    return -1;

  while ((ent = readdir(dir)) != NULL) {
    if (!uv__fs_scandir_filter((const uv__dirent_t*) ent))
      continue;
    dent = uv__malloc(sizeof(*dent));
    if (dent == NULL) {
      closedir(dir);
      while (n > 0)
        uv__free(dents[--n]);
      uv__free(dents);
      errno = ENOMEM;
      return -1;
    }
    memcpy(dent, ent, sizeof(*dent));
    if (n == allocated) {
      uv__dirent_t** tmp;
      allocated = allocated ? allocated * 2 : 16;
      tmp = uv__realloc(dents, allocated * sizeof(*dents));
      if (tmp == NULL) {
        uv__free(dent);
        closedir(dir);
        while (n > 0)
          uv__free(dents[--n]);
        uv__free(dents);
        errno = ENOMEM;
        return -1;
      }
      dents = tmp;
    }
    dents[n++] = dent;
  }
  closedir(dir);

  if (n > 1)
    qsort(dents, n, sizeof(*dents),
          (int (*)(const void*, const void*)) uv__fs_scandir_sort);

  req->nbufs = 0;
  req->ptr = dents;
  return (ssize_t) n;
#else
  uv__dirent_t** dents;
  int n;

  dents = NULL;
  n = scandir(req->path, &dents, uv__fs_scandir_filter,
              (int (*)(const void*, const void*)) uv__fs_scandir_sort);
'''
assert old in s
s = s.replace(old, new)

old2 = '''  req->ptr = dents;

  return n;
}

static int uv__fs_opendir(uv_fs_t* req) {'''
new2 = '''  req->ptr = dents;

  return n;
#endif /* __QNX__ */
}

static int uv__fs_opendir(uv_fs_t* req) {'''
assert old2 in s
s = s.replace(old2, new2)
open(p, 'w').write(s)
print('patched libuv fs.c: QNX scandir emulation')
