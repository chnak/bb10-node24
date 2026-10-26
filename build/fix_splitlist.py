import glob, re

NEW = '''function(split_list list_name)
  string(REPLACE ";" " " out "${${list_name}}")
  set(${list_name} "${out}" PARENT_SCOPE)
endfunction()
'''

files = glob.glob('/opt/build/src/libcxxabi-18.1.3.src/cmake/Modules/*.cmake') + \
        glob.glob('/opt/build/src/libcxx-18.1.3.src/cmake/Modules/*.cmake')

pat = re.compile(r'function\(split_list list_name\).*?endfunction\(\)\n', re.S)
for f in files:
    s = open(f).read()
    if 'function(split_list list_name)' in s:
        s2 = pat.sub(NEW, s, count=1)
        open(f, 'w').write(s2)
        print('fixed', f)
