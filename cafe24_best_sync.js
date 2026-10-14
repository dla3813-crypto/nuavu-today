// [베스트 2단계] best_ids.json(GitHub) → 카페24 베스트 카테고리(cate_no 69) 를 그 목록으로 교체 (순서 = 매출 순위)
// 크롬 탭 https://nuavu.cafe24api.com/... 에서 javascript_tool 로 실행. 결과: window.__best = {done, want, had, added, removed, ordered(순서 지정 성공 수), errs}
// 전제: 카테고리 69 는 수동 진열(product_display_type 'U') — 2026-10-14 전환 완료. 자동 진열이면 순서 지정이 422 로 실패함.
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
    // 순서 지정: 카테고리는 수동 진열(product_display_type U)이어야 함. API 는 상품 1개씩 sequence 로 지정 (요청제한 1건)
    let ordered=0;
    for(let i=0;i<want.length;i++){
      let r=await fetch('/api/v2/admin/categories/'+CAT+'/products',{method:'PUT',headers:H,body:JSON.stringify({shop_no:1,request:{display_group:1,product_no:want[i],sequence:i+1}})});
      if(r.status===429){ await sleep(1200); r=await fetch('/api/v2/admin/categories/'+CAT+'/products',{method:'PUT',headers:H,body:JSON.stringify({shop_no:1,request:{display_group:1,product_no:want[i],sequence:i+1}})}); }
      if(r.ok) ordered++; else if(errs.length<8) errs.push('seq '+want[i]+' '+r.status+' '+(await r.text()).slice(0,80));
      await sleep(120);
    }
    window.__best={done:true,want:want.length,had:have.size,added,removed,ordered,errs:errs.slice(0,8)};
    console.log(window.__best);
  }catch(e){ window.__best={done:true,err:String(e)}; }
})();
