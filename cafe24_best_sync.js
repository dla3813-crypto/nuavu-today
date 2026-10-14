// [베스트 2단계] best_ids.json(GitHub) → 카페24 베스트 카테고리(cate_no 69) 를 그 목록으로 교체 (순서 = 매출 순위)
// 크롬 탭 https://nuavu.cafe24api.com/... 에서 javascript_tool 로 실행. 결과: window.__best = {done, want, had, added, removed, ordered, err}
(async()=>{
  window.__best={done:false};
  try{
    const CAT=69, sleep=ms=>new Promise(r=>setTimeout(r,ms));
    let tok=JSON.parse(localStorage.getItem('nv_tok'));
    if(new Date(tok.expires_at+'+09:00')-Date.now()<15*60*1000){ const r=await fetch('/api/v2/oauth/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded','Authorization':'Basic '+btoa(localStorage.getItem('nv_client')+':'+localStorage.getItem('nv_secret'))},body:new URLSearchParams({grant_type:'refresh_token',refresh_token:tok.refresh_token})}); const j=await r.json(); if(!j.access_token) throw new Error('TOKEN_REFRESH_FAIL'); localStorage.setItem('nv_tok',JSON.stringify(j)); tok=j; }
    const H={'Authorization':'Bearer '+tok.access_token,'Content-Type':'application/json'};
    const best=await (await fetch('https://dla3813-crypto.github.io/nuavu-today/best_ids.json?v='+Date.now())).json();
    const nos=best.items.map(x=>x.no); if(nos.length<10) throw new Error('BEST_TOO_FEW '+nos.length);
    // 진열·판매 중인 상품만
    const pj=await (await fetch('/api/v2/admin/products?product_no='+nos.join(',')+'&limit=100&fields=product_no,display,selling',{headers:H})).json();
    const ok=new Set((pj.products||[]).filter(p=>p.display==='T'&&p.selling==='T').map(p=>p.product_no));
    const want=nos.filter(n=>ok.has(n));
    const lj=await (await fetch('/api/v2/admin/categories/'+CAT+'/products?display_group=1&limit=5000',{headers:H})).json();
    const have=new Set((lj.products||[]).map(p=>p.product_no));
    let added=0, removed=0, errs=[];
    for(const n of [...have].filter(n=>!want.includes(n))){ const r=await fetch('/api/v2/admin/categories/'+CAT+'/products/'+n+'?display_group=1',{method:'DELETE',headers:H}); if(r.ok) removed++; else errs.push('del '+n+' '+r.status); await sleep(350); }
    const add=want.filter(n=>!have.has(n));
    for(let i=0;i<add.length;i+=100){ const b=add.slice(i,i+100); const r=await fetch('/api/v2/admin/categories/'+CAT+'/products',{method:'POST',headers:H,body:JSON.stringify({shop_no:1,request:{display_group:1,product_no:b}})}); if(r.status===201) added+=b.length; else errs.push('add '+r.status); await sleep(500); }
    // 순서 고정 시도 (지원 안 되면 무시)
    let ordered=false;
    try{ const r=await fetch('/api/v2/admin/categories/'+CAT+'/products',{method:'PUT',headers:H,body:JSON.stringify({shop_no:1,request:{display_group:1,product_no:want,auto_sort:'F',fixed_sort:'T'}})}); ordered=r.ok; if(!r.ok) errs.push('order '+r.status+' '+(await r.text()).slice(0,100)); }catch(e){ errs.push('order '+e); }
    window.__best={done:true,want:want.length,had:have.size,added,removed,ordered,errs:errs.slice(0,5)};
  }catch(e){ window.__best={done:true,err:String(e)}; }
})();
