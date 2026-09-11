#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare two OCCT testgrid runs (stock kernel vs patched kernel).

Reads tests.log of each run, extracts the per-case status lines
    CASE <group> <grid> <case>: <STATUS...>
and joins them on (group, grid, case).

Classification of a difference, from the point of view of the patch:
  better           - stock not OK  -> patched OK
  worse            - stock OK      -> patched not OK
  merely different - both non-OK, but the status text changed
                     (or a case appears in only one of the runs)
"""
import re
import sys
import os

CASE_RE = re.compile(r'^CASE\s+(\S+)\s+(\S+)\s+(\S+):\s*(.*?)\s*$')


def load(path):
    """Return {(group, grid, case): status_text}."""
    out = {}
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            m = CASE_RE.match(line.strip())
            if m:
                group, grid, case, status = m.groups()
                out[(group, grid, case)] = status
    return out


def is_ok(status):
    # OCCT marks a clean pass as "OK"; everything else (FAILED, IMPROVEMENT,
    # SKIPPED, BAD ...) is not a clean pass.
    return status.split()[0] == 'OK' if status else False


def main(stock_log, patched_log):
    stock = load(stock_log)
    patched = load(patched_log)

    keys = sorted(set(stock) | set(patched))
    same = better = worse = different = 0
    rows = []

    for k in keys:
        s = stock.get(k)
        p = patched.get(k)
        if s == p:
            same += 1
            continue
        if s is None or p is None:
            verdict = 'merely different'
            different += 1
        elif not is_ok(s) and is_ok(p):
            verdict = 'better'
            better += 1
        elif is_ok(s) and not is_ok(p):
            verdict = 'worse'
            worse += 1
        else:
            verdict = 'merely different'
            different += 1
        rows.append((k, s, p, verdict))

    print('=' * 78)
    print('cases in stock run   : %d' % len(stock))
    print('cases in patched run : %d' % len(patched))
    print('identical status     : %d' % same)
    print('differing status     : %d' % len(rows))
    print('  better             : %d' % better)
    print('  worse              : %d' % worse)
    print('  merely different   : %d' % different)
    print('=' * 78)
    print('stock  OK count      : %d' % sum(1 for v in stock.values() if is_ok(v)))
    print('patched OK count     : %d' % sum(1 for v in patched.values() if is_ok(v)))
    print('=' * 78)

    if rows:
        print('\nDIFFERENCES')
        for (group, grid, case), s, p, verdict in rows:
            print('-' * 78)
            print('%-8s %s %s %s' % (verdict.upper(), group, grid, case))
            print('  stock  : %s' % s)
            print('  patched: %s' % p)
    else:
        print('\nNo status differences at all.')

    return 0


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('usage: compare_runs.py <stock tests.log> <patched tests.log>')
        sys.exit(2)
    for f in sys.argv[1:]:
        if not os.path.isfile(f):
            print('missing file: %s' % f)
            sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
