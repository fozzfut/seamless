import sys, importlib.util
spec=importlib.util.spec_from_file_location('cl', r'C:\dev\seamless\tests-fillet\compare_logs.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
a=m.case_logs(sys.argv[1]); b=m.case_logs(sys.argv[2])
for rel in sorted(set(a)&set(b)):
    if m.clean(a[rel])!=m.clean(b[rel]): print(rel)
