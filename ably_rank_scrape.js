// [랭킹 1단계] 에이블리 실시간 상품 랭킹 긁기 — 크롬 탭에서 아래 URL 을 연 뒤 javascript_tool 로 실행 (로그인 불필요)
// https://mobile.a-bly.com/screens?screen_name=COMPONENT_LIST&next_token=eyJsIjogMTEsICJwIjogeyJtYXJrZXRfc25vIjogMjkzNzl9fQ%3D%3D
// 결과: ~/Downloads/rank_raw.json  [{rank,sno,name}]  /  window.__rs = {done, n}
(async()=>{
  await new Promise(r=>setTimeout(r,1500));
  for(let i=0;i<4;i++){ window.scrollTo(0,document.body.scrollHeight); await new Promise(r=>setTimeout(r,700)); }   // 추가 로딩
  const seen=new Set();
  const items=[...document.querySelectorAll('a[href*="/goods/"]')].map(a=>({sno:+a.href.match(/goods\/(\d+)/)[1],name:a.innerText.replace(/\s+/g,' ').trim().replace(/^누아브\s*/,'')}))
    .filter(x=>x.sno && !seen.has(x.sno) && seen.add(x.sno)).map((x,i)=>({rank:i+1,sno:x.sno,name:x.name}));
  const blob=new Blob([JSON.stringify(items)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='rank_raw.json'; document.body.appendChild(a); a.click();
  window.__rs={done:true,n:items.length};
})();
