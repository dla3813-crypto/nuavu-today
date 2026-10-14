#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""에이블리 실시간 랭킹(rank_raw.json: [{rank,sno,name}]) → 카페24 상품번호 매칭 → rank_ids.json
사용: python3 rank_match.py --raw ~/mnt/Downloads/rank_raw.json --map map.json --goods <nuavu-reviews>/goods_map.json --out rank_ids.json
매칭: goods_map(에이블리 sno→product_no) 우선, 없으면 상품명 정규화 비교. 미매칭은 제외."""
import json, re, argparse

def norm(s):
    s = str(s or ''); s = s.replace('당일출고', ''); s = re.sub(r'\[[^\]]*\]', '', s); s = re.sub(r'\([^)]*\)', '', s); s = re.sub(r'[^\w가-힣]', '', s); return s.lower()

def to_no(c):
    n = 0
    for ch in c[1:]: n = n * 26 + (0 if ch == '0' else ord(ch) - 65)
    return n

ap = argparse.ArgumentParser(); ap.add_argument('--raw', required=True); ap.add_argument('--map', required=True); ap.add_argument('--goods'); ap.add_argument('--out', required=True); ap.add_argument('--max', type=int, default=20)
a = ap.parse_args()
raw = json.load(open(a.raw, encoding='utf-8'))
mp = json.load(open(a.map, encoding='utf-8')); byname = {}
for p in mp: byname.setdefault(norm(p['name']), (to_no(p['code']), p['code']))
gm = {int(k): v for k, v in json.load(open(a.goods, encoding='utf-8')).items()} if a.goods else {}
code_of = {to_no(p['code']): p['code'] for p in mp}
out = []; miss = []
for r in raw:
    no = gm.get(r['sno']); code = code_of.get(no)
    if not no:
        hit = byname.get(norm(r['name']))
        if hit: no, code = hit
    if no: out.append({'rank': len(out) + 1, 'no': no, 'code': code, 'ably': r['name']})
    else: miss.append(r['name'])
    if len(out) >= a.max: break
json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False)
print(f'rank {len(out)} matched / unmatched {len(miss)}: {miss[:5]}')
