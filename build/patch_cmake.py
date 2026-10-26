import sys, os

MACROS = {
    "split_list": '''function(split_list list_name)
  set(out "")
  foreach(item ${${list_name}})
    separate_arguments(parts UNIX_COMMAND "${item}")
    list(APPEND out ${parts})
  endforeach()
  set(${list_name} "${out}" PARENT_SCOPE)
endfunction()

''',
    "mangle_name": '''macro(mangle_name str output)
  string(STRIP "${str}" strippedStr)
  string(REGEX REPLACE "^[^A-Za-z0-9_]+" "" strippedStr "${strippedStr}")
  string(REGEX REPLACE "[^A-Za-z0-9_]+" "_" strippedStr "${strippedStr}")
  set(${output} "${strippedStr}")
endmacro()

''',
}

path = sys.argv[1]
s = open(path).read()
added = []
for name, body in MACROS.items():
    if ("macro(%s" % name) not in s and ("function(%s" % name) not in s:
        # insert before the first macro/function definition
        idx = s.find("macro(")
        if idx < 0:
            idx = s.find("function(")
        if idx < 0:
            idx = 0
        s = s[:idx] + body + s[idx:]
        added.append(name)
open(path, "w").write(s)
print("patched %s: %s" % (path, ",".join(added) if added else "nothing"))
