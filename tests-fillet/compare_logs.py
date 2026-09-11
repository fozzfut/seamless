#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diff the per-case logs of two OCCT testgrid runs (stock kernel vs patched kernel).

Timing/memory lines are volatile between runs of the same binary, so they are
filtered out before comparison; everything else -- validity, volumes, areas,
bounding boxes, sub-shape counts, error text -- is compared verbatim.
"""
import os
import re
import sys
import difflib

# Lines that differ between two runs of the *same* binary and carry no geometry.
VOLATILE = re.compile(
    r'(CPU user time|CPU system time|Elapsed time|Total CPU time|MEMORY DELTA|'
    r'Memory (delta|heap)|TOTAL CPU|Tcl Exception|^\s*$|'
    r'DRAW\[|Debug mode|seconds|elapsed)', re.IGNORECASE)


def case_logs(root):
    """Return {(grid, case): path} for every *.log under root/<group>/<grid>/."""
    found = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith('.log'):
                continue
            if fn in ('tests.log',):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace('\\', '/')
            found[rel] = full
    return found


# "An exception was caught 000001FCAAD71E60 : ..." -- the hex is the address of
# the exception object inside that process, so it differs between any two runs,
# including two runs of the very same binary. Normalise it away.
ADDR = re.compile(r'\b[0-9A-F]{8,16}\b')


def clean(path):
    out = []
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.rstrip('\r\n')
            if VOLATILE.search(line):
                continue
            out.append(ADDR.sub('<ADDR>', line))
    return out


def main(stock_root, patched_root, show=40):
    a = case_logs(stock_root)
    b = case_logs(patched_root)

    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    both = sorted(set(a) & set(b))

    identical, differing = [], []
    for rel in both:
        la, lb = clean(a[rel]), clean(b[rel])
        if la == lb:
            identical.append(rel)
        else:
            differing.append((rel, la, lb))

    print('=' * 78)
    print('case logs, stock   : %d' % len(a))
    print('case logs, patched : %d' % len(b))
    print('compared           : %d' % len(both))
    print('byte-identical     : %d' % len(identical))
    print('differing          : %d' % len(differing))
    print('only in stock      : %d %s' % (len(only_a), only_a[:5]))
    print('only in patched    : %d %s' % (len(only_b), only_b[:5]))
    print('=' * 78)

    for rel, la, lb in differing[:show]:
        print('\n' + '-' * 78)
        print('DIFF %s' % rel)
        print('-' * 78)
        for line in difflib.unified_diff(la, lb, 'stock', 'patched',
                                         lineterm='', n=2):
            print(line)

    if len(differing) > show:
        print('\n... %d further differing cases not printed' %
              (len(differing) - show))
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: compare_logs.py <stock dir> <patched dir> [show]')
        sys.exit(2)
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    sys.exit(main(sys.argv[1], sys.argv[2], n))
