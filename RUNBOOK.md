# 누아브 오늘출발 JSON 30분 갱신 — 실행 절차 (예약 작업용)

목표: 이지어드민 현재고를 받아 `p/*.json`·`index.json`·`today_codes.json`을 만들고 GitHub(dla3813-crypto/nuavu-today)에 푸시한다.
소요: 이지어드민 다운로드 작업 ~20초~1분 + 처리 10초. 전체 2~3분.

## 0. 전제
- 크롬(Claude in Chrome)에 이지어드민(ga79.ezadmin.co.kr) 로그인 세션이 살아 있어야 한다. 로그인 화면이면 **중단하고 사장님께 알린다** (다른 작업 금지).
- 연결 폴더: `~/Desktop/클로드` — 이 작업 파일은 전부 하위 폴더 **`카페24오늘출발 갱신/`** 에 있음 (github_token.txt, cafe24_secret.txt, build_today.py, cafe24_category_sync.js, 이 절차서). `~/Downloads` 는 크롬 다운로드 위치.
- 작업 폴더는 세션 VM의 `$HOME/nuavu-today` (매 실행 새로 clone, 5MB).
- 크롬 탭은 이 작업용으로 새로 만들고, 끝나면 닫는다. 이지어드민 세션 유지용 탭은 건드리지 않는다.

## 1. 이지어드민 다운로드 신청
1. `https://ga79.ezadmin.co.kr/template35.htm?template=I100` 열기.
2. JS로 필터 세팅 후 검색 (공급처 누아브·자체제작, 정상재고 1 이상):
   ```js
   document.querySelector('[name=query_type]').value='name';
   document.querySelector('[name=query_str]').value='';
   document.querySelector('[name=multi_supply]').value='20003,20171';   // 누아브, 자체제작
   document.querySelector('#str_supply_code').value='0';
   document.querySelector('[name=stock_type]').value='0';                // 정상재고
   document.querySelector('[name=stock_start]').value='1';
   document.querySelector('[name=stock_end]').value='';
   window.search();
   ```
   5~6초 후 하단 "보기 1 - 100 / N" 의 N이 1,000~3,000 사이면 정상 (5,000 이상이면 재고 필터 실패, 20,000 이상이면 공급처 필터 실패 → 재시도).
3. `find`로 "다운로드(F6)" 요소를 찾아 클릭 → "다운로드 변경 안내" 모달. **이 모달은 DOM/접근성 트리에 잡히지 않는다.** 스크린샷을 찍고 파란 "다운로드 신청" 버튼을 좌표 클릭 (1186×1008 프레임 기준 대략 (605,530); 스크린샷에서 위치를 확인해 보정). 제목이 "다운로드 접수 안내"로 바뀌면 성공 → "닫기"(대략 (716,502)).

## 2. 완료 대기 → 파일 받기
1. `https://ga79.ezadmin.co.kr/template40.htm?template=BL30` (다운로드관리자) 열기.
2. 첫 행이 "완료 100%"가 될 때까지 15초 간격으로 새로고침(최대 5분). 파일명 `현재고조회_YYYYMMDDHHMMSS_*.xls`.
3. 그 파일명 링크를 JS로 `.click()` → 크롬이 `~/Downloads`에 저장 (5초 대기).

## 3. (선택) 카페24 신상 반영 — map.json에 없는 상품
크롬에서 `https://m.nuavu.kr/product/list.html?cate_no=50` (ALL, 최신순) 1페이지를 열고:
```js
const known = await (await fetch('https://dla3813-crypto.github.io/nuavu-today/map.json?v='+Date.now())).json();
const codes = new Set(known.map(p=>p.code));
function toCode(no){var n=+no,s='',A='ABCDEFGHIJKLMNOPQRSTUVWXYZ';do{s=A[n%26]+s;n=Math.floor(n/26);}while(n>0);while(s.length<7)s='0'+s;return 'P'+s;}
const nos=[...new Set([...document.querySelectorAll('.nv-badge[data-no]')].map(e=>e.getAttribute('data-no')))].filter(no=>!codes.has(toCode(no)));
const out=[];
for(const no of nos){ const t=await (await fetch('/product/detail.html?product_no='+no)).text();
  const m=t.match(/option_stock_data\s*=\s*'([^']+)'/); if(!m) continue;
  const d=JSON.parse(m[1].replace(/\\"/g,'"').replace(/\\\\/g,'\\'));
  const name=(t.match(/<title>([^<]*)<\/title>/)||[])[1].replace(/ - 누아브$/,'');
  out.push({code:toCode(no), name, opts:Object.values(d).map(o=>String(o.option_value))}); }
JSON.stringify(out)
```
결과가 `[]`가 아니면 그 JSON을 VM의 `$HOME/nuavu-today/new_products.json`에 저장하고 3단계에서 `--extra new_products.json`을 붙인다. (`option_stock_data` 파싱이 실패하면 그 상품은 건너뛰고 보고.)

## 4. JSON 생성 + 푸시 (device_bash)
```bash
D="$(ls -d $HOME/mnt/*/ | grep -v -E 'Claude|Downloads' | head -1)카페24오늘출발 갱신"     # 클로드/카페24오늘출발 갱신 폴더(한글 경로는 glob로)
T=$(tr -d '\r\n ' < "$D/github_token.txt")
F=$(ls -t "$HOME/mnt/Downloads"/현재고조회_*.xls | head -1)
cd $HOME && rm -rf nuavu-today && git clone -q --depth 1 "https://x-access-token:${T}@github.com/dla3813-crypto/nuavu-today.git"
cd nuavu-today && cp "$D/build_today.py" . 2>/dev/null
python3 build_today.py --ez "$F" --out .            # 신상이 있으면 --extra new_products.json 추가
git config user.email dla3813@gmail.com && git config user.name nuavu-bot
git add -A && git commit -qm "재고 갱신 $(TZ=Asia/Seoul date '+%m-%d %H:%M')" && git push -q "https://x-access-token:${T}@github.com/dla3813-crypto/nuavu-today.git" main
```
- 출력 `ok MM.DD HH:MM: 상품 N / 옵션 M / 오늘출발 K` 확인. **오늘출발 K가 0이거나 직전 대비 절반 이하면 푸시하지 말고 보고**(파일 깨짐·필터 오류 의심).
- 변경이 없으면 index.json만 바뀌므로 커밋은 항상 1개.

## 4.5 카페24 "오늘출발" 카테고리(cate_no=58) 동기화 — 크롬에서 API 호출
VM/컨테이너는 nuavu.cafe24api.com 접근이 막혀 있으므로 **크롬 탭에서** 카페24 Admin API를 부른다.
1. 푸시 후 **90초 대기** (GitHub Pages 반영). 크롬에서 `https://dla3813-crypto.github.io/nuavu-today/index.json?v=<now>` 의 updated 가 방금 값인지 확인(아니면 30초 더).
2. 새 크롬 탭으로 `https://nuavu.cafe24api.com/api/v2/admin/categories/58` 열기 (401 JSON이 보이면 정상). 이 origin 의 localStorage 에 `nv_client`, `nv_secret`(앱 시크릿, **절대 읽거나 출력하지 않는다**), `nv_tok`(토큰), `nv_sync_src`(동기화 함수 소스)가 저장돼 있다.
3. javascript_tool 로 실행:
   ```js
   eval('window.nvSync = ' + localStorage.getItem('nv_sync_src')); await nvSync();
   ```
   (nv_sync_src 가 없으면 `카페24오늘출발 갱신/cafe24_category_sync.js` 전문을 실행.)
   함수 동작: 토큰 만료 20분 전이면 refresh → today_codes.json 을 받아 product_no 로 변환(26진수 역변환) → 카테고리 58 현재 목록(`?display_group=1&limit=5000`, offset 미지원)과 비교 → 없는 것 POST(100개씩, 422 중복이면 낱개 재시도) / 빠진 것 DELETE.
4. 결과 문자열 `카테고리 동기화: 오늘출발 W / 기존 H / 추가 A / 제외 D` 를 보고에 붙인다.
   - `TOKEN_REFRESH_FAIL` / `NO_TOKEN` → 카테고리 단계만 건너뛰고 "카페24 앱 인증 다시 필요"라고 보고 (재고 JSON 갱신은 정상 완료로 취급).
   - `TODAY_CODES_SUSPICIOUS` / `LIST_INCOMPLETE` → 카테고리 단계 건너뛰고 보고.
   - 앱 인증 재발급: 크롬에서 `https://nuavu.cafe24api.com/api/v2/oauth/authorize?response_type=code&client_id=1DK7wM6zAVCosDzoPDSJ5A&state=nv&redirect_uri=https://dla3813-crypto.github.io/nuavu-today/oauth.html&scope=mall.read_category,mall.write_category,mall.read_product,mall.write_product` → 사장님이 동의함 클릭 → oauth.html 의 code 를 1분 안에 위 탭에서 `grant_type=authorization_code` 로 교환해 `nv_tok` 에 저장 (cafe24_category_sync.js 상단 주석 참고; refresh 토큰은 2주).

## 5. 다운로드 폴더 정리
- `~/Downloads/현재고조회_*.xls` 전부 삭제 (`device_request_delete_permission` ~/Downloads, 사유: 이지어드민 재고 xls 정리). 권한이 없으면 `~/Downloads/_ezadmin_old/`로 `mv -n` 하고 보고.

## 6. 보고 규칙
- 정상: 한 줄 (`갱신 완료 HH:MM — 상품 N / 오늘출발 K / 카테고리 추가 A 제외 D`).
- 이상(로그인 풀림, 다운로드 5분 초과, 푸시 실패, K 급감): 무엇이 막혔는지 한 줄 + 사장님 조치 필요 여부.

## 7. 검증(가끔)
- 크롬에서 `https://dla3813-crypto.github.io/nuavu-today/index.json` 의 updated 확인 (VM/컨테이너는 github.io 접근 불가).
- 카페24 상품 엑셀을 새로 받으면 `--cafe24 파일.csv`로 한 번 돌려 map.json을 통째로 갱신(신상 자동 수집분 포함해 정리됨).
