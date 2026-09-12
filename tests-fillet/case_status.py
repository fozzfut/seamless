import os,re,sys,collections
# testgrid writes "CASE <group> <grid> <case>: <STATUS> (...)" as the last line of each case log
CASE=re.compile(r'^CASE\s+(\S+)\s+(\S+)\s+(\S+):\s+(.+?)\s*$')
def statuses(root):
    st={}
    for dp,_,fns in os.walk(root):
        for fn in fns:
            if not fn.endswith('.log') or fn=='tests.log': continue
            p=os.path.join(dp,fn)
            last=None
            for line in open(p,encoding='utf-8',errors='replace'):
                m=CASE.match(line.strip())
                if m: last=m
            if last:
                st['%s/%s'%(last.group(2),last.group(3))]=last.group(4)
    return st
a=statuses(sys.argv[1]); b=statuses(sys.argv[2])
print('cases stock=%d cond=%d'%(len(a),len(b)))
ca=collections.Counter(v.split('(')[0].strip() for v in a.values())
cb=collections.Counter(v.split('(')[0].strip() for v in b.values())
print('stock:',dict(ca)); print('cond :',dict(cb))
diff=[(k,a[k],b.get(k)) for k in sorted(set(a)|set(b)) if a.get(k)!=b.get(k)]
print('status differences:',len(diff))
for k,x,y in diff: print('  %-40s stock=%-30s cond=%s'%(k,x,y))
skipped=sorted(k for k,v in a.items() if v.startswith('SKIPPED'))
print('skipped (%d):'%len(skipped))
for k in skipped: print('   ',k,'|',a[k])
notok=sorted(k for k,v in a.items() if not v.startswith('OK') and not v.startswith('SKIPPED'))
print('non-OK executed (%d):'%len(notok))
for k in notok: print('   %-40s %s'%(k,a[k]))
