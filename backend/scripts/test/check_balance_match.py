#!/usr/bin/env python3
import json

data = json.load(open('header_manipulation_results.json'))

clean = [r for r in data['results'] if not r['is_manipulated']]
manipulated = [r for r in data['results'] if r['is_manipulated']]

print('Sample balance_match values from clean statements:')
for r in clean[:10]:
    print(f"  run_id={r['run_id']}, balance_match={r['balance_match']}, change_ratio={r['balance_diff_change_ratio']:.4f}")

print()
print(f"Clean statements balance_match breakdown:")
print(f"  balance_match=1: {sum(1 for r in clean if r['balance_match'] == 1)}")
print(f"  balance_match='Passed': {sum(1 for r in clean if r['balance_match'] == 'Passed')}")
print(f"  balance_match=0 or 'Failed': {sum(1 for r in clean if r['balance_match'] in [0, 'Failed'])}")

if manipulated:
    print()
    print(f"Manipulated statements balance_match breakdown:")
    print(f"  balance_match=1: {sum(1 for r in manipulated if r['balance_match'] == 1)}")
    print(f"  balance_match='Passed': {sum(1 for r in manipulated if r['balance_match'] == 'Passed')}")
    print(f"  balance_match=0 or 'Failed': {sum(1 for r in manipulated if r['balance_match'] in [0, 'Failed'])}")
