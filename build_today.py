#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
누아브 오늘출발 JSON 생성기
  입력: 이지어드민 현재고조회 xls(HTML)  +  카페24 상품 엑셀 CSV(옵션 매핑용, 있을 때만 갱신)
  출력: p/<카페24상품코드>.json  = {"u": "MM.DD HH:MM", "o": {"색상-사이즈": 1|0|-1}}
        index.json               = 요약(생성시각, 상품수, 오늘출발 옵션수)
  판정: 가용 = 정상재고 - 송장 - 접수 ; 정상재고>=9999(무한) 또는 가용>0 → 1(오늘출발), 그 외 0(일반배송)
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

    ez = read_ezadmin(a.ez)
    exact, loose = {}, {}
    for x in ez:
        exact.setdefault((x['nn'], x['opt']), []).append(x)
        loose.setdefault((x['nn'], fz(x['opt'])), []).append(x)

    now = datetime.datetime.now(KST).strftime('%m.%d %H:%M')   # 항상 한국시간
    pdir = os.path.join(a.out, 'p'); os.makedirs(pdir, exist_ok=True)
    n_prod = n_today = n_opt = 0
    written = set()
    for p in products:
        o = {}
        for opt in p['opts']:
            cand = exact.get((p['nn'], opt)) or loose.get((p['nn'], fz(opt)))
            if cand:
                o[opt] = status(cand)
        if not o:
            continue   # 이지어드민에 없는 상품 → 파일 없음 → 위젯 숨김
        n_prod += 1; n_opt += len(o); n_today += sum(1 for v in o.values() if v == 1)
        fn = os.path.join(pdir, p['code'] + '.json')
        body = json.dumps({'u': now, 'o': o}, ensure_ascii=False, separators=(',', ':'))
        old = open(fn, encoding='utf-8').read() if os.path.exists(fn) else ''
        # 옵션 상태가 안 바뀌면 시각만 달라지므로 그대로 두어 커밋 최소화
        if not old or json.loads(old)['o'] != o:
            open(fn, 'w', encoding='utf-8').write(body)
        written.add(p['code'] + '.json')
    for f in os.listdir(pdir):
        if f.endswith('.json') and f not in written:
            os.remove(os.path.join(pdir, f))
    json.dump({'updated': now, 'products': n_prod, 'options': n_opt, 'today': n_today},
              open(os.path.join(a.out, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'ok {now}: 상품 {n_prod} / 옵션 {n_opt} / 오늘출발 {n_today}')

if __name__ == '__main__':
    main()
