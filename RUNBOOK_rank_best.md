# 에이블리 실시간 랭킹(매일) + 베스트 카테고리(매주 화요일) 갱신 — 실행 절차 (예약 작업용)

파일: 연결 폴더 `~/Desktop/클로드/카페24오늘출발 갱신/` (이 절차서, ably_rank_scrape.js, rank_match.py, cafe24_rank_enrich.js, ably_best_scrape.js, best_match.py, cafe24_best_sync.js, github_token.txt).
전제: 크롬에 에이블리 셀러(my.a-bly.com) 로그인 세션(베스트 단계만 필요), 카페24 앱 토큰(nuavu.cafe24api.com localStorage nv_tok). 토큰·시크릿 값은 절대 출력하지 않는다. 작업용 탭은 새로 열고 끝나면 닫는다.

## 0. 저장소 준비 (device_bash)
```bash
D="$(ls -d $HOME/mnt/*/ | grep -v -E 'Claude|Downloads' | head -1)카페24오늘출발 갱신"; T=$(tr -d '\r\n ' < "$D/github_token.txt")
cd $HOME && rm -rf nuavu-today nuavu-reviews
git clone -q --depth 1 "https://x-access-token:${T}@github.com/dla3813-crypto/nuavu-today.git" && git clone -q --depth 1 "https://x-access-token:${T}@github.com/dla3813-crypto/nuavu-reviews.git"
cd nuavu-today && git config user.email dla3813@gmail.com && git config user.name nuavu-bot && mkdir -p "$HOME/mnt/Downloads/_ezadmin_old"
TZ=Asia/Seoul date '+%A'     # Tuesday 면 2부(베스트)도 수행
```

## 1부. 실시간 상품 랭킹 (매일)
1. 크롬 새 탭 `https://mobile.a-bly.com/screens?screen_name=COMPONENT_LIST&next_token=eyJsIjogMTEsICJwIjogeyJtYXJrZXRfc25vIjogMjkzNzl9fQ%3D%3D` (로그인 불필요) → `ably_rank_scrape.js` 전문 실행 → `window.__rs.done` 확인. `n` < 10 이면 1부 중단·보고.
2. device_bash:
   ```bash
   cd $HOME/nuavu-today && python3 "$D/rank_match.py" --raw "$HOME/mnt/Downloads/rank_raw.json" --map map.json --goods $HOME/nuavu-reviews/goods_map.json --out rank_ids.json
   git add -A && git commit -qm "랭킹 매칭" && git push -q "https://x-access-token:${T}@github.com/dla3813-crypto/nuavu-today.git" main
   mv -n "$HOME/mnt/Downloads/rank_raw.json" "$HOME/mnt/Downloads/_ezadmin_old/rank_raw_$(date +%s).json"
   ```
   60초 대기(Pages 반영).
3. 크롬 새 탭 `https://nuavu.cafe24api.com/api/v2/admin/categories/58` (401 JSON 정상) → `cafe24_rank_enrich.js` 전문 실행 → `window.__rk.done` 확인(30초). NO_TOKEN/TOKEN 오류면 "카페24 앱 인증 다시 필요" 보고.
4. device_bash: `cd $HOME/nuavu-today && cp "$HOME/mnt/Downloads/ranking.json" . && git add -A && git commit -qm "ranking 갱신" && git push -q "https://x-access-token:${T}@github.com/dla3813-crypto/nuavu-today.git" main && mv -n "$HOME/mnt/Downloads/ranking.json" "$HOME/mnt/Downloads/_ezadmin_old/ranking_$(date +%s).json"`

## 2부. 베스트 카테고리(cate_no 69) — 화요일만
1. 기간 = 어제까지 7일. device_bash 로 날짜 계산: `S=$(TZ=Asia/Seoul date -d '7 days ago' +%F); E=$(TZ=Asia/Seoul date -d 'yesterday' +%F); echo $S $E`
2. 크롬 새 탭 `https://my.a-bly.com/statistics/sales/goods?option_enable=false&page=1&per_page=100&start_date=<S>&end_date=<E>` → 로그인 화면이면 "에이블리 로그인 풀림" 보고하고 2부 중단. 표가 100행 그려진 뒤(3초) `ably_best_scrape.js` 전문 실행 → `window.__bs.done`, `n` 이 50 미만이면 중단·보고.
3. device_bash:
   ```bash
   cd $HOME/nuavu-today && python3 "$D/best_match.py" --raw "$HOME/mnt/Downloads/best_raw.json" --map map.json --out best_ids.json
   git add -A && git commit -qm "베스트 매칭" && git push -q "https://x-access-token:${T}@github.com/dla3813-crypto/nuavu-today.git" main
   mv -n "$HOME/mnt/Downloads/best_raw.json" "$HOME/mnt/Downloads/_ezadmin_old/best_raw_$(date +%s).json"
   ```
   60초 대기.
4. 크롬 cafe24api 탭에서 `cafe24_best_sync.js` 전문 실행 → `window.__best.done` 확인(1~2분). 카테고리 69 를 목록으로 교체(추가/제외)하고 순서 고정을 시도한다(`ordered:false` 면 보고에 적는다).

## 보고
- 정상: 한 줄 `랭킹 갱신 완료 — N개` (화요일: `+ 베스트 M개 (추가 A 제외 D, 순서 고정 O)`). 알림 없이 조용히 끝낸다.
- 이상: 무엇이 막혔는지 한 줄 + 사장님 조치 필요 여부.
