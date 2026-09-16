#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
누아브 오늘출발 JSON 생성기
  입력: 이지어드민 현재고조회 xls(HTML)  +  카페24 상품 엑셀 CSV(옵션 매핑용, 있을 때만 갱신)
  출력: p/<카페24상품코드>.json  = {"u": "MM.DD HH:MM", "o": {"색상-사이즈": 1|0|-1}}
        index.json               = 요약(생성시각, 상품수, 오늘출발 옵션수)
        today_codes.json         = 오늘출발 옵션이 1개 이상인 카페24 상품코드 배열 (목록 썸네일 배지용)
  판정: 가용 = 정상재고 - 송장 - 접수 ; 정상재고>=9999(무한) 또는 가용>0 → 1(오늘출발), 그 외 0(일반배송)
        이지어드민 파일은 '정상재고 ≥ 1' 필터로 받아도 됨(빠진 옵션 = 0 = 일반배송으로 처리)
  중복코드: 같은 상품·옵션이 대표상품코드 여러 개면 정상재고>=1인 코드 우선
사용:
  python3 build_today.py --ez 현재고조회.xls [--cafe24 nuavu_xxx.csv] --out <저장소 폴더>
"""
import argparse, csv, io, itertools, json, os, re, sys, datetime
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')

SUPPLIERS = {'누아브', '자체제작'}   # 이지어드민 공급처 중 누아브 자사몰 상품이 있는 곳
INFINITE = 9999

def norm_name(s):
    s = str(s or '').strip()
    s = re.sub(r'^\(?[A-Z]{1,3}-\d+\)?\s*', '', s)   # (NA-9) 로케이션 접두
    s = re.sub(r'^\([^)]*\)', '', s)                 # 기타 ( ) 접두
    s = re.sub(r'\[[^\]]*\]', '', s)                 # [2color] 등 태그
    s = re.sub(r'[^\w가-힣]', '', s)                  # 공백·기호 제거
    return s.lower()

def fz(s):  # 옵션 느슨 비교용
    return re.sub(r'[\s&★+\-()\[\]]', '', str(s)).lower()

def read_cafe24(path):
    """카페24 상품 CSV → [(상품코드, 정규화상품명, [옵션문자열...])]"""
    raw = open(path, 'rb').read()
    txt = raw.decode('utf-8-sig') if raw[:3] == b'\xef\xbb\xbf' else raw.decode('cp949', errors='replace')
    rows = list(csv.DictReader(io.StringIO(txt)))
    out = []
    for r in rows:
        if r.get('진열상태') != 'Y':
            continue
        parts = re.findall(r'\{([^}]*)\}', r.get('옵션입력', ''))
        combos = ['-'.join(c) for c in itertools.product(*[p.split('|') for p in parts])] if parts else []
        out.append({'code': r['상품코드'], 'name': r['상품명'], 'nn': norm_name(r['상품명']), 'opts': combos})
    return out

def read_ezadmin(path):
    """이지어드민 현재고조회 xls(HTML 테이블) → 행 리스트"""
    import pandas as pd
    tables = pd.read_html(path, encoding='utf-8')
    df = max(tables, key=len).astype(str)
    df.columns = df.iloc[0]; df = df.iloc[1:]
    df = df[df['공급처'].isin(SUPPLIERS)].copy()
    rows = []
    for _, r in df.iterrows():
        def num(x):
            try: return float(x)
            except: return 0.0
        rows.append({'nn': norm_name(r['상품명']), 'opt': str(r['옵션']).strip('[] '),
                     'stock': num(r['정상재고']), 'inv': num(r['송장']), 'recv': num(r['접수']),
                     'code': r['대표상품코드']})
    return rows

def status(rows):
    """같은 (상품,옵션) 후보 여러 개 → 정상재고>=1 우선"""
    pick = [x for x in rows if x['stock'] >= 1] or rows
    x = pick[0]
    if x['stock'] >= INFINITE: return 1
    return 1 if (x['stock'] - x['inv'] - x['recv']) > 0 else 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ez', required=True)
    ap.add_argument('--cafe24')
    ap.add_argument('--extra', help='신상 추가분 JSON [{code,name,opts:[...]}] (브라우저에서 수집) → map.json에 병합')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    map_path = os.path.join(a.out, 'map.json')
    if a.cafe24:
        products = read_cafe24(a.cafe24)
        json.dump(products, open(map_path, 'w', encoding='utf-8'), ensure_ascii=False)
    elif os.path.exists(map_path):
        products = json.load(open(map_path, encoding='utf-8'))
    else:
        sys.exit('map.json 없음: 처음엔 --cafe24 상품CSV 필요')
    if a.extra and os.path.exists(a.extra):
        known = {p['code'] for p in products}
        added = 0
        for x in json.load(open(a.extra, encoding='utf-8')):
            if x.get('code') and x['code'] not in known and x.get('opts'):
                products.append({'code': x['code'], 'name': x['name'], 'nn': norm_name(x['name']), 'opts': x['opts']}); added += 1
        if added:
            json.dump(products, open(map_path, 'w', encoding='utf-8'), ensure_ascii=False)
            print(f'map.json 신상 {added}개 추가')

    ez = read_ezadmin(a.ez)
    exact, loose = {}, {}
    for x in ez:
        exact.setdefault((x['nn'], x['opt']), []).append(x)
        loose.setdefault((x['nn'], fz(x['opt'])), []).append(x)

    now = datetime.datetime.now(KST).strftime('%m.%d %H:%M')   # 항상 한국시간
    pdir = os.path.join(a.out, 'p'); os.makedirs(pdir, exist_ok=True)
    n_prod = n_today = n_opt = 0
    written = set(); today_codes = []
    for p in products:
        o = {}
        for opt in p['opts']:
            cand = exact.get((p['nn'], opt)) or loose.get((p['nn'], fz(opt)))
            if cand:
                o[opt] = status(cand)
        if not o:
            o = {opt: 0 for opt in p['opts']}   # 이지어드민에 없거나(정상재고≥1 필터로 빠진) 상품 → 전 옵션 일반배송
            if not o:
                continue
        n_prod += 1; n_opt += len(o); n_today += sum(1 for v in o.values() if v == 1)
        if any(v == 1 for v in o.values()): today_codes.append(p['code'])
        fn = os.path.join(pdir, p['code'] + '.json')
        body = json.dumps({'u': now, 'o': o}, ensure_ascii=False, separators=(',', ':'))
        old = open(fn, encoding='utf-8').read() if os.path.exists(fn) else ''
        # 옵션 상태가 안 바뀐 파일은 건드리지 않음(커밋 최소화). 갱신 시각은 index.json이 기준
        if not old or json.loads(old)['o'] != o:
            open(fn, 'w', encoding='utf-8').write(body)
        written.add(p['code'] + '.json')
    for f in os.listdir(pdir):
        if f.endswith('.json') and f not in written:
            os.remove(os.path.join(pdir, f))
    json.dump(sorted(today_codes), open(os.path.join(a.out, 'today_codes.json'), 'w', encoding='utf-8'), separators=(',', ':'))   # 목록 배지용
    json.dump({'updated': now, 'products': n_prod, 'options': n_opt, 'today': n_today},
              open(os.path.join(a.out, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'ok {now}: 상품 {n_prod} / 옵션 {n_opt} / 오늘출발 {n_today}')

if __name__ == '__main__':
    main()
