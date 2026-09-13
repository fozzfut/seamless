#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
edge9_table.py <outroot> [run_index]

Reads the per-radius logs of run_edge9_proof.sh and prints the seven-radius table of the
owner's part side by side for every kernel that was run.  A radius whose log has no RESULT
line is reported as TIMEOUT/NO_RESULT -- that is a measurement, not a gap.
"""
import os, re, sys

RAD = ('0.1', '0.25', '0.45', '0.5', '0.55', '1.0', '2.0')


def load(d):
    """{radius_string: dict of key=value from the RESULT line}"""
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in os.listdir(d):
        m = re.match(r'^r(.+)\.log$', fn)
        if not m:
            continue
        r = m.group(1)
        txt = open(os.path.join(d, fn), encoding='utf-8', errors='replace').read()
        line = [l for l in txt.splitlines() if l.startswith('RESULT ')]
        if not line:
            out[r] = {'status': 'TIMEOUT/NO_RESULT'}
            continue
        kv = {}
        for tok in line[-1].split()[1:]:
            if '=' in tok:
                k, v = tok.split('=', 1)
                kv[k] = v
        out[r] = kv
    return out


def main(root, idx='1'):
    kernels = [k for k in ('stock', 'cond', 'blunt') if os.path.isdir(os.path.join(root, k + idx))]
    data = {k: load(os.path.join(root, k + idx)) for k in kernels}
    hdr = '%-7s' % 'radius'
    for k in kernels:
        hdr += ' | %-52s' % k
    print(hdr)
    print('-' * len(hdr))
    for r in RAD:
        row = '%-7s' % r
        for k in kernels:
            d = data[k].get(r, {})
            if not d:
                cell = 'no log'
            elif 'vol' not in d or d.get('vol') == '-':
                cell = d.get('status', '?')
            else:
                cell = '%-22s v=%-5s vol=%-12s d=%-11s %s' % (
                    d.get('status', '?'), d.get('valid', '?'), d.get('vol', '?'),
                    d.get('delta', '?'), d.get('bop', '?'))
            row += ' | %-52s' % cell
        print(row)
    print()
    for k in kernels:
        d = data[k].get('1.0', {})
        if 'ideal' in d and 'vol' in d and d['vol'] != '-':
            print('%-6s r=1.0  vol=%s  ideal=%s  diff=%+.6f' %
                  (k, d['vol'], d['ideal'], float(d['vol']) - float(d['ideal'])))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '1')
