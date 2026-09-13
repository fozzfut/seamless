#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic classification of the difference between two runs of the generated
"seamless" group (stock kernel vs patched kernel).

For every case it extracts three facts from the case log:
    built   - was a fillet produced at all (RESULT_BUILT yes/no)
    valid   - did checkshape call the result valid
    mass    - the volume reported by vprops

and classifies the change:
    better           not built -> built, or invalid -> valid
    worse            built -> not built, or valid -> invalid
    merely different only the numbers moved
    same             nothing moved
"""
import os
import re
import sys

RE_BUILT = re.compile(r'^RESULT_BUILT (yes|no)', re.M)
RE_CHECK = re.compile(r'^CHECKSHAPE (.*)$', re.M)
RE_MASS = re.compile(r'^Mass :\s+(\S+)', re.M)


def facts(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    m = RE_BUILT.search(text)
    built = m.group(1) if m else 'absent'
    m = RE_CHECK.search(text)
    check = m.group(1).strip() if m else ''
    valid = 'seems to be valid' in check
    masses = RE_MASS.findall(text)
    mass = masses[0] if masses else None
    return built, valid, mass, check


def collect(root):
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.endswith('.log') and fn != 'tests.log':
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root).replace('\\', '/')
                out[rel] = facts(full)
    return out


def main(stock_root, patched_root):
    a, b = collect(stock_root), collect(patched_root)
    common = sorted(set(a) & set(b))

    buckets = {'same': [], 'better': [], 'worse': [], 'merely different': []}

    for rel in common:
        (ba, va, ma, ca) = a[rel]
        (bb, vb, mb, cb) = b[rel]
        if (ba, va, ma) == (bb, vb, mb):
            buckets['same'].append(rel)
        elif (ba != 'yes' and bb == 'yes') or (not va and vb):
            buckets['better'].append((rel, a[rel], b[rel]))
        elif (ba == 'yes' and bb != 'yes') or (va and not vb):
            buckets['worse'].append((rel, a[rel], b[rel]))
        else:
            buckets['merely different'].append((rel, a[rel], b[rel]))

    print('=' * 78)
    print('cases compared    : %d' % len(common))
    for k in ('same', 'better', 'worse', 'merely different'):
        print('%-18s: %d' % (k, len(buckets[k])))
    print('=' * 78)
    print('stock   : built=%d valid=%d' % (
        sum(1 for v in a.values() if v[0] == 'yes'),
        sum(1 for v in a.values() if v[1])))
    print('patched : built=%d valid=%d' % (
        sum(1 for v in b.values() if v[0] == 'yes'),
        sum(1 for v in b.values() if v[1])))
    print('=' * 78)

    for k in ('better', 'worse', 'merely different'):
        if not buckets[k]:
            continue
        print('\n### %s (%d)' % (k.upper(), len(buckets[k])))
        for rel, fa, fb in buckets[k]:
            print('  %s' % rel)
            print('     stock  : built=%s valid=%s mass=%s' % (fa[0], fa[1], fa[2]))
            print('     patched: built=%s valid=%s mass=%s' % (fb[0], fb[1], fb[2]))
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('usage: classify.py <stock dir> <patched dir>')
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
