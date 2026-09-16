// 누아브 오늘출발 → 카페24 "오늘출발" 카테고리(cate_no=58) 동기화
// 실행 위치: 크롬 탭 https://nuavu.cafe24api.com/ (이 origin 의 localStorage 에 nv_client / nv_secret / nv_tok 저장됨)
// 사용: 이 파일 전체를 javascript_tool 로 실행 → 마지막 줄 결과가 요약 문자열
// 앱 인증 재발급(토큰 교환) — oauth.html 에서 받은 code 로, 같은 탭에서 1분 안에:
//   const r=await fetch('/api/v2/oauth/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded','Authorization':'Basic '+btoa(localStorage.getItem('nv_client')+':'+localStorage.getItem('nv_secret'))},body:new URLSearchParams({grant_type:'authorization_code',code:'<CODE>',redirect_uri:'https://dla3813-crypto.github.io/nuavu-today/oauth.html'})});
//   const j=await r.json(); if(j.access_token) localStorage.setItem('nv_tok',JSON.stringify(j)); ({ok:!!j.access_token, expires_at:j.expires_at})   // 토큰 값은 출력하지 않는다
// 시크릿 최초 저장: 페이지에 <input type=password> 를 만들어 사장님이 직접 붙여넣고 localStorage.nv_secret 에 저장 (대화에 값이 남지 않게)
async function nvSync(){
  const CAT=58, V='2025-06-01', sleep=ms=>new Promise(r=>setTimeout(r,ms));
  let tok=JSON.parse(localStorage.getItem('nv_tok')||'null'); if(!tok) return 'NO_TOKEN (nv_tok 없음 → 앱 인증 다시 필요)';
  if(new Date(tok.expires_at+'+09:00') - Date.now() < 20*60*1000){   // 만료 20분 전이면 갱신 (refresh 토큰 2주)
    const r=await fetch('/api/v2/oauth/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded','Authorization':'Basic '+btoa(localStorage.getItem('nv_client')+':'+localStorage.getItem('nv_secret'))},body:new URLSearchParams({grant_type:'refresh_token',refresh_token:tok.refresh_token})});
    const j=await r.json(); if(!j.access_token) return 'TOKEN_REFRESH_FAIL '+r.status+' '+(j.error||'')+' → 앱 인증 다시 필요'; localStorage.setItem('nv_tok',JSON.stringify(j)); tok=j;
  }
  const H={'Authorization':'Bearer '+tok.access_token,'Content-Type':'application/json','X-Cafe24-Api-Version':V};
  const toNo=c=>{let n=0;for(const ch of c.slice(1))n=n*26+(ch==='0'?0:ch.charCodeAt(0)-65);return n;};
  const codes=await (await fetch('https://dla3813-crypto.github.io/nuavu-today/today_codes.json?v='+Date.now())).json();
  if(!Array.isArray(codes)||codes.length<50) return 'TODAY_CODES_SUSPICIOUS '+(codes&&codes.length)+' → 동기화 중단';
  const want=new Set(codes.map(toNo));
  const cnt=(await (await fetch(`/api/v2/admin/categories/${CAT}/products/count?display_group=1`,{headers:H})).json()).count;
  const lj=await (await fetch(`/api/v2/admin/categories/${CAT}/products?display_group=1&limit=5000`,{headers:H})).json();   // offset 미지원 → limit 크게
  const have=new Set((lj.products||[]).map(p=>p.product_no));
  if(have.size<cnt) return `LIST_INCOMPLETE ${have.size}/${cnt} → 동기화 중단`;
  const add=[...want].filter(n=>!have.has(n)), del=[...have].filter(n=>!want.has(n)); let added=0, deleted=0, errs=[];
  const post=async b=>{const r=await fetch(`/api/v2/admin/categories/${CAT}/products`,{method:'POST',headers:H,body:JSON.stringify({shop_no:1,request:{display_group:1,product_no:b}})}); return r;};
  for(let i=0;i<add.length;i+=100){ const b=add.slice(i,i+100); const r=await post(b);
    if(r.status===201) added+=b.length;
    else if(r.status===422){ for(const n of b){ const r2=await post([n]); if(r2.status===201) added++; else if(r2.status!==422) errs.push('add '+n+' '+r2.status); await sleep(300);} }   // 일부 중복 → 낱개 재시도
    else errs.push('add '+r.status+' '+(await r.text()).slice(0,120));
    await sleep(500);}
  for(const n of del){ const r=await fetch(`/api/v2/admin/categories/${CAT}/products/${n}?display_group=1`,{method:'DELETE',headers:H}); if(r.ok) deleted++; else errs.push('del '+n+' '+r.status); await sleep(400);}
  return `카테고리 동기화: 오늘출발 ${want.size} / 기존 ${have.size} / 추가 ${added} / 제외 ${deleted}` + (errs.length?' / 오류 '+errs.length+': '+errs.slice(0,3).join(' | '):'');
}
await nvSync();
