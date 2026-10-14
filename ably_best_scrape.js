// [베스트 1단계] 에이블리 상품별 매출 통계(최근 7일, 거래액순 상위 100) 긁기 — 크롬에서 my.a-bly.com 로그인 상태로 실행
// 먼저 아래처럼 날짜를 계산해 페이지를 연다 (어제까지 7일):  https://my.a-bly.com/statistics/sales/goods?option_enable=false&page=1&per_page=100&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
// 페이지가 다 그려진 뒤 javascript_tool 로 실행 → ~/Downloads/best_raw.json [{rank,name,sales,qty}] / window.__bs={done,n,period}
(async()=>{
  await new Promise(r=>setTimeout(r,1500));
  const th=[...document.querySelectorAll('table thead th')].map(t=>t.innerText.trim());
  const iName=th.indexOf('상품명'), iSales=th.indexOf('거래액'), iQty=th.indexOf('판매수량');
  const num=s=>+String(s||'').replace(/[^\d]/g,'')||0;
  const rows=[...document.querySelectorAll('table tbody tr')].map(tr=>[...tr.querySelectorAll('td')]).filter(td=>td.length>iQty);
  const items=rows.map((td,i)=>({rank:i+1,name:td[iName].innerText.trim(),sales:num(td[iSales].innerText),qty:num(td[iQty].innerText)})).filter(x=>x.name);
  const q=new URLSearchParams(location.search);
  const blob=new Blob([JSON.stringify({period:[q.get('start_date'),q.get('end_date')],items})],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='best_raw.json'; document.body.appendChild(a); a.click();
  window.__bs={done:true,n:items.length,period:[q.get('start_date'),q.get('end_date')]};
})();
