# 누아브 오늘출발 JSON 30분 갱신 — 실행 절차 (예약 작업용)

목표: 이지어드민 현재고를 받아 `p/*.json`·`index.json`을 만들고 GitHub(dla3813-crypto/nuavu-today)에 푸시한다.
소요: 이지어드민 다운로드 작업 ~1분 + 처리 10초. 전체 3~4분.

## 0. 전제
- 크롬(Claude in Chrome)에 이지어드민(ga79.ezadmin.co.kr) 로그인 세션이 살아 있어야 한다. 로그인 화면이면 중단하고 사장님께 알린다.
- 연결 폴더: `~/Desktop/클로드` (github_token.txt, build_today.py), `~/Downloads` (크롬 다운로드 위치).
- 작업 폴더는 세션 VM의 `$HOME/nuavu-today` (매 실행 새로 clone — 5MB).

## 1. 이지어드민 다운로드 신청
1. `https://ga79.ezadmin.co.kr/template35.htm?template=I100` 열기.
2. JS로 공급처 필터 세팅 후 검색:
   ```js
   document.querySelector('[name=query_type]').value='name';
   document.querySelector('[name=query_str]').value='';
   document.querySelector('[name=multi_supply]').value='20003,20171';   // 누아브, 자체제작
   document.querySelector('#str_supply_code').value='0';
   window.search();
   ```
   5~6초 후 하단 "보기 1 - 100 / N" 의 N이 5,000 이상이면 정상 (전체 29,000이면 필터 실패 → 재시도).
3. `find`로 "다운로드(F6)" 요소를 찾아 클릭 → "다운로드 변경 안내" 모달이 뜬다. **이 모달은 DOM/접근성 트리에 잡히지 않는다.** 스크린샷을 찍고 파란 "다운로드 신청" 버튼 위치를 좌표 클릭한다(1186×1008 프레임 기준 대략 (605,530)). 클릭 후 제목이 "다운로드 접수 안내"로 바뀌면 성공, 그 뒤 "닫기".

## 2. 완료 대기 → 파일 받기
1. `https://ga79.ezadmin.co.kr/template40.htm?template=BL30` (다운로드관리자) 열기.
2. 첫 행이 "완료 100%"가 될 때까지 20초 간격으로 새로고침(최대 6분). 파일명은 `현재고조회_YYYYMMDDHHMMSS_*.xls`.
3. 그 파일명 링크를 JS로 `.click()` → 크롬이 `~/Downloads`에 저장 (5~6초).

## 3. JSON 생성 + 푸시 (device_bash)
```bash
D=$(ls -d $HOME/mnt/*/ | grep -v -E 'Claude|Downloads' | head -1)     # 클로드 폴더(한글 경로는 glob로)
T=$(tr -d '\r\n ' < "$D/github_token.txt")
F=$(ls -t "$HOME/mnt/Downloads"/현재고조회_*.xls | head -1)
cd $HOME && rm -rf nuavu-today && git clone -q --depth 1 "https://x-access-token:${T}@github.com/dla3813-crypto/nuavu-today.git"
cd nuavu-today && python3 build_today.py --ez "$F" --out .
git config user.email dla3813@gmail.com && git config user.name nuavu-bot
git add -A && git commit -qm "재고 갱신 $(TZ=Asia/Seoul date '+%m-%d %H:%M')" && git push -q "https://x-access-token:${T}@github.com/dla3813-crypto/nuavu-today.git" main
```
- 출력 `ok MM.DD HH:MM: 상품 N / 옵션 M / 오늘출발 K` 확인. 상품 수가 직전 대비 20% 이상 줄면 푸시하지 말고 보고(파일 깨짐 의심).
- 변경이 없으면 index.json만 바뀌므로 커밋은 항상 1개.

## 4. 다운로드 폴더 정리
- `~/Downloads/현재고조회_*.xls` 중 방금 쓴 파일 포함 전부 삭제 (삭제 권한 필요: `device_request_delete_permission` ~/Downloads). 권한이 없으면 `~/Downloads/_ezadmin_old/`로 이동하고 보고.

## 5. 검증(가끔)
- `https://dla3813-crypto.github.io/nuavu-today/index.json` 의 updated가 방금 시각인지 (크롬에서 확인; VM/컨테이너는 github.io 접근 불가).
- 카페24 신상이 추가되면 `map.json`이 옛것이라 그 상품 위젯이 안 뜬다 → 카페24 상품 엑셀을 새로 받아 `--cafe24 파일.csv` 옵션으로 한 번 돌려 map.json 갱신.
