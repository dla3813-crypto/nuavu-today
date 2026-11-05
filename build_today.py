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
import argparse, csv, io, itertools, json, os, re, sys, datetime, unicodedata
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')

SUPPLIERS = {'누아브', '자체제작'}   # 이지어드민 공급처 중 누아브 자사몰 상품이 있는 곳
INFINITE = 9999

def _read_json(path):
    with open(path,encoding='utf-8') as stream:return json.load(stream)

def _write_json(path,value,**options):
    with open(path,'w',encoding='utf-8') as stream:json.dump(value,stream,**options)

_LOCATION = r'[A-Za-z]{1,3}-\d+(?:\.\d+)?'
_LOCATIONS = re.compile(r'^(?:'+_LOCATION+r')(?:\s*[,/]\s*'+_LOCATION+r')*$', re.I)
_BARE_LOCATION = re.compile(r'^'+_LOCATION+r'(?=\s|\[|\(|$)\s*', re.I)
_PROMOTIONS = frozenset(('기획특가','특가','초특가','기획','기획상품','묶음할인','세트할인','할인',
                         '신상','신상품','오늘출발','당일출고','당일발송','빠른배송','무료배송','기획전'))
_DISPLAY = frozenset(('모델착용','모델피팅','오늘출발','당일출고','당일발송'))

def _text(s):
    return unicodedata.normalize('NFKC', str(s or '')).strip()

def _metadata(s):
    """Only quantity/promotion labels; unknown product attributes retain identity."""
    parts=[re.sub(r'\s+','',x).casefold() for x in re.split(r'[,/·+]',s)]
    return bool(parts) and all(p in _PROMOTIONS or re.fullmatch(r'\d+(?:color|colors|size|sizes|컬러|사이즈)',p)
                               for p in parts)

def norm_name(s):
    s = _text(s).lstrip('★* ')
    while s:
        bracket=re.match(r'^([\[(])([^\])]*)([\])])\s*',s)
        if bracket and ((bracket[1]=='(' and bracket[3]==')') or (bracket[1]=='[' and bracket[3]==']')):
            if _LOCATIONS.fullmatch(bracket[2].strip()) or _metadata(bracket[2]):
                s=s[bracket.end():].lstrip('★* ');continue
        bare=_BARE_LOCATION.match(s)
        if bare:s=s[bare.end():].lstrip('★* ');continue
        break
    # A known display/count label is equally harmless in the middle of a name.
    s=re.sub(r'\[([^\]]*)\]',lambda m:'' if _metadata(m[1]) else m[0],s)
    return re.sub(r'[^\w가-힣]','',s).casefold()

def legacy_name(s):
    """Compatibility identity, usable only for a unique product on both sides."""
    s=_text(s)
    s=re.sub(r'^\([^)]*\)\s*','',s)
    s=re.sub(r'^[A-Z]{1,3}-[\d.]+\s*','',s)
    s=re.sub(r'\[[^\]]*\]','',s)
    return re.sub(r'[^\w가-힣]','',s).casefold()

def _name_versions(s):
    return tuple(sorted(re.findall(r'신버전|구버전|리뉴얼|\d+세대',_text(s))))

def _name_semantic_conflict(left,right):
    for alternatives in (('긴팔','반팔','간팔'),('겨울','여름')):
        a={word for word in alternatives if word in _text(left)}
        b={word for word in alternatives if word in _text(right)}
        if a and b and not a&b:return True
    return False

def _unknown_name_tags(s):
    return {re.sub(r'[^\w가-힣]','',part).casefold() for x in re.findall(r'\[([^\]]*)\]',_text(s))
            if not _metadata(x) and not _LOCATIONS.fullmatch(x.strip())
            for part in re.split(r'[,+]',x) if part.strip()}

def canonical_option(s):
    """Preserve color/size and old/new version, allowing only cosmetic reordering."""
    s=_text(s)
    def display(m):
        return '' if re.sub(r'\s+','',m[1]) in _DISPLAY else m[0]
    s=re.sub(r'\(([^()]*)\)',display,s)
    s=re.sub(r'\[([^\[\]]*)\]',display,s)
    versions=re.findall(r'(?<![\w가-힣])(신버전|구버전)(?![\w가-힣])',s)
    if len(versions)>1:return None
    s=re.sub(r'(?<![\w가-힣])(신버전|구버전)(?![\w가-힣])','',s)
    s=s.replace('★','')
    # English and Korean one-color labels describe the same single-color option.
    s=re.sub(r'(?i)one\s*color','원컬러',s)
    body=re.sub(r'[\s\[\]()\-/_,·&+]','',s).casefold()
    return (versions[0] if versions else '',body) if body else None

def fz(s):  # 옵션 느슨 비교용
    return re.sub(r'[\s&★+\-()\[\]]', '', str(s)).lower()

def read_cafe24(path):
    """카페24 상품 CSV → [(상품코드, 정규화상품명, [옵션문자열...])]"""
    raw = Path(path).read_bytes()
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
        child=str(r.get('상품코드','')).strip()
        if child.casefold() in ('','nan','none'):child=str(r['대표상품코드'])
        rows.append({'nn': norm_name(r['상품명']), 'name':str(r['상품명']), 'opt': str(r['옵션']).strip('[] '),
                     'stock': num(r['정상재고']), 'inv': num(r['송장']), 'recv': num(r['접수']),
                     'code':child})
    return rows

def status(rows):
    """같은 (상품,옵션) 후보 여러 개 → 정상재고>=1 우선"""
    pick = [x for x in rows if x['stock'] >= 1] or rows
    x = pick[0]
    if x['stock'] >= INFINITE: return 1
    return 1 if (x['stock'] - x['inv'] - x['recv']) > 0 else 0

def _resolved_status(rows,legacy=False):
    """Keep the active-code preference, but never guess across conflicting rows."""
    pick=[x for x in rows if x['stock']>=1] or rows
    by_code={}
    for x in pick:
        identity=(x.get('stock'),x.get('inv'),x.get('recv'))
        code=str(x.get('code',''))
        if code in by_code and by_code[code]!=identity:return None
        by_code[code]=identity
    if not legacy and len({status([x]) for x in pick})>1:return None
    return status(pick)

def match_products(products,ez,force=()):
    exact,canonical,legacy={}, {}, {}
    retail_names={}
    for p in products:retail_names.setdefault(legacy_name(p.get('name','')),set()).add(norm_name(p.get('name','')))
    ez_names={}
    for x in ez:
        exact.setdefault((x['nn'],x['opt']),[]).append(x)
        key=canonical_option(x['opt'])
        if key is not None:canonical.setdefault((x['nn'],key),[]).append(x)
        if x.get('name'):
            ln=legacy_name(x['name']);ez_names.setdefault(ln,set()).add(x['nn'])
            if key is not None:legacy.setdefault((ln,key),[]).append(x)
    diagnostics={'unmatchedOptions':0,'ambiguousOptions':0,'matchedOptions':0,'legacyNameAliasOptions':0,'examples':[],'ambiguousExamples':[]}
    matched=[];force=set(force)
    for p in products:
        nn=norm_name(p.get('name',''));ln=legacy_name(p.get('name',''))
        keys=Counter(canonical_option(opt) for opt in p['opts'])
        o={opt:0 for opt in p['opts']}
        for opt in p['opts']:
            key=canonical_option(opt)
            direct=exact.get((nn,opt))
            if direct:
                value=status(direct);why='exact'
            elif key is not None and keys[key]>1:
                why='ambiguous_retail_option';value=None
            else:
                cand=canonical.get((nn,key)) if key is not None else None
                alias=False;ambiguous_name=False
                if not cand and key is not None:
                    possible=legacy.get((ln,key))
                    if possible and len(retail_names.get(ln,()))==len(ez_names.get(ln,()))==1:
                        name=p.get('name','');tags=_unknown_name_tags(name)
                        other=possible[0].get('name','');other_tags=_unknown_name_tags(other)
                        if (_name_versions(name)==_name_versions(other)
                                and not _name_semantic_conflict(name,other)
                                and not(tags and other_tags and not(tags<=other_tags or other_tags<=tags))):
                            cand=possible;alias=True
                    elif possible:ambiguous_name=True
                legacy_option=bool(cand and legacy_name(p.get('name',''))==legacy_name(cand[0].get('name',''))
                    and all(fz(x['opt'])==fz(opt) for x in cand))
                value=_resolved_status(cand,legacy=legacy_option) if cand else None
                why='conflicting_inventory' if cand else 'ambiguous_product_identity' if ambiguous_name else 'unmatched'
                if alias and value is not None:diagnostics['legacyNameAliasOptions']+=1
            if value is None:
                count='unmatchedOptions' if why=='unmatched' else 'ambiguousOptions'
                diagnostics[count]+=1
                example={'code':p['code'],'option':opt,'reason':why}
                if len(diagnostics['examples'])<30:diagnostics['examples'].append(example)
                if why!='unmatched' and len(diagnostics['ambiguousExamples'])<30:diagnostics['ambiguousExamples'].append(example)
            else:o[opt]=value;diagnostics['matchedOptions']+=1
        if p['code'] in force:o={opt:1 for opt in o}
        matched.append({'code':p['code'],'options':o})
    return matched,diagnostics

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ez', required=True)
    ap.add_argument('--cafe24')
    ap.add_argument('--extra', help='신상 추가분 JSON [{code,name,opts:[...]}] (브라우저에서 수집) → map.json에 병합')
    ap.add_argument('--out', required=True)
    ap.add_argument('--diagnostics', help='선택: 매칭 진단 JSON 저장 경로(게시 파일에 자동 추가하지 않음)')
    a = ap.parse_args()

    map_path = os.path.join(a.out, 'map.json')
    if a.cafe24:
        products = read_cafe24(a.cafe24)
        _write_json(map_path,products,ensure_ascii=False)
    elif os.path.exists(map_path):
        products = _read_json(map_path)
    else:
        sys.exit('map.json 없음: 처음엔 --cafe24 상품CSV 필요')
    if a.extra and os.path.exists(a.extra):
        bycode = {p['code']: p for p in products}
        added = updated = 0
        for x in _read_json(a.extra):
            if not (x.get('code') and x.get('opts')):
                continue
            if x['code'] in bycode:                                  # 이미 있는 상품 → 옵션/상품명 갱신 (옵션 변경 반영)
                cur = bycode[x['code']]
                if cur.get('opts') != x['opts'] or cur.get('name') != x['name']:
                    cur['opts'] = x['opts']; cur['name'] = x['name']; cur['nn'] = norm_name(x['name']); updated += 1
            else:
                products.append({'code': x['code'], 'name': x['name'], 'nn': norm_name(x['name']), 'opts': x['opts']}); added += 1
        if added or updated:
            _write_json(map_path,products,ensure_ascii=False)
            print(f'map.json 신상 {added}개 추가 / 옵션 갱신 {updated}개')

    ez = read_ezadmin(a.ez)

    fpath = os.path.join(a.out, 'force_today.json')             # ["P00000WK", ...] 항상 오늘출발 처리할 카페24 상품코드
    force = set(_read_json(fpath)) if os.path.exists(fpath) else set()
    now = datetime.datetime.now(KST).strftime('%m.%d %H:%M')   # 항상 한국시간
    pdir = os.path.join(a.out, 'p'); os.makedirs(pdir, exist_ok=True)
    n_prod = n_today = n_opt = 0
    written = set(); today_codes = []
    matches,diagnostics=match_products(products,ez,force)
    for p in matches:
        o=p['options']
        if not o:continue
        n_prod += 1; n_opt += len(o); n_today += sum(1 for v in o.values() if v == 1)
        if any(v == 1 for v in o.values()): today_codes.append(p['code'])
        fn = os.path.join(pdir, p['code'] + '.json')
        body = json.dumps({'u': now, 'o': o}, ensure_ascii=False, separators=(',', ':'))
        old = Path(fn).read_text(encoding='utf-8') if os.path.exists(fn) else ''
        # 옵션 상태가 안 바뀐 파일은 건드리지 않음(커밋 최소화). 갱신 시각은 index.json이 기준
        if not old or json.loads(old)['o'] != o:
            Path(fn).write_text(body,encoding='utf-8')
        written.add(p['code'] + '.json')
    for f in os.listdir(pdir):
        if f.endswith('.json') and f not in written:
            os.remove(os.path.join(pdir, f))
    _write_json(os.path.join(a.out,'today_codes.json'),sorted(today_codes),separators=(',',':'))
    _write_json(os.path.join(a.out,'index.json'),{'updated':now,'products':n_prod,'options':n_opt,'today':n_today},ensure_ascii=False)
    if a.diagnostics:
        with open(a.diagnostics,'w',encoding='utf-8') as stream:json.dump(diagnostics,stream,ensure_ascii=False,indent=2)
    print('매칭 진단: 연결 '+str(diagnostics['matchedOptions'])+' / 미등록 '+str(diagnostics['unmatchedOptions'])+' / 확인 필요 '+str(diagnostics['ambiguousOptions']))
    print(f'ok {now}: 상품 {n_prod} / 옵션 {n_opt} / 오늘출발 {n_today}')

if __name__ == '__main__':
    main()
