#!/usr/bin/env python

''' Script for precomputing the optimal (shortest path) policy at each viewpoint. '''

from env import R2RBatch
import json
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--dir', default='./data/v1/scans')
parser.add_argument('--split', default='train')
args = parser.parse_args()

r2r = R2RBatch(None, batch_size=1, splits=[args.split])

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if os.path.isdir(path):
            pass
        else: raise

for scan in r2r.paths:
    for goal in r2r.paths[scan]:
        mkdir_p('{}/{}/policies'.format(args.dir, scan))
        with open('{}/{}/policies/{}.json'.format(args.dir, scan, goal), 'w') as f:
            f.write(json.dumps(r2r.paths[scan][goal]))

