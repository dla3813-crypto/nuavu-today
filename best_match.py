#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""에이블리 매출 통계(best_raw.json: {period, items:[{rank,name,sales,qty}]}) → 카페24 상품번호 매칭 → best_ids.json
사용: python3 best_match.py --raw ~/mnt/Downloads/best_raw.json --map map.json --out best_ids.json [--max 100]
매칭: 상품명 정규화 비교(괄호/대괄호 태그·'당일출고' 접두 무시). 미매칭·진열 안 된 상품은 제외(진열 여부는 카페24 쪽 스크립트가 다시 거름)."""
import json, re, argparse

def norm(s):
    s = str(s or ''); s = s.replace('당일출고', ''); s = re.sub(r'\[[^\]]*\]', '', s); s = re.sub(r'\([^)]*\)', '', s); s = re.sub(r'[^\w가-힣]', '', s); return s.lower()

def to_no(c):
    n = 0
    for ch in c[1:]: n = n * 26 + (0 if ch == '0' else ord(ch) - 65)
    return n

ap = argparse.ArgumentParser(); ap.add_argument('--raw', required=True); ap.add_argument('--map', required=True); ap.add_argument('--out', required=True); ap.add_argument('--max', type=int, default=100)
a = ap.parse_args()
raw = json.load(open(a.raw, encoding='utf-8'))
byname = {}
for p in json.load(open(a.map, encoding='utf-8')): byname.setdefault(norm(p['name']), (to_no(p['code']), p['code'], p['name']))
out = []; miss = []
for r in raw['items']:
    hit = byname.get(norm(r['name']))
    if hit: out.append({'rank': len(out) + 1, 'no': hit[0], 'code': hit[1], 'name': hit[2], 'sales': r.get('sales'), 'qty': r.get('qty')})
    else: miss.append(r['name'])
    if len(out) >= a.max: break
json.dump({'period': raw.get('period'), 'items': out}, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False)
print(f"best {len(out)} matched / unmatched {len(miss)}: {miss[:6]}")
