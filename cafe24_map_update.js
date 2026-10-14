// [절차서 3단계] 카페24 상품 목록(map.json) 보강 — 크롬 탭 https://nuavu.cafe24api.com/... 에서 javascript_tool 로 실행
// 진열 중인 상품 중 map.json 에 없는 상품의 옵션을 API 로 받아 ~/Downloads/new_products.json 으로 저장 ([{code,name,opts:[...]}])
// 결과: window.__map = {done, displayed, missing, added, err}
(async()=>{
  window.__map={done:false};
  try{
    let tok=JSON.parse(localStorage.getItem('nv_tok'));
    if(new Date(tok.expires_at+'+09:00')-Date.now()<15*60*1000){ const r=await fetch('/api/v2/oauth/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded','Authorization':'Basic '+btoa(localStorage.getItem('nv_client')+':'+localStorage.getItem('nv_secret'))},body:new URLSearchParams({grant_type:'refresh_token',refresh_token:tok.refresh_token})}); const j=await r.json(); if(j.access_token){localStorage.setItem('nv_tok',JSON.stringify(j)); tok=j;} }
    const H={'Authorization':'Bearer '+tok.access_token}; const sleep=ms=>new Promise(r=>setTimeout(r,ms));
    const known=new Set((await (await fetch('https://dla3813-crypto.github.io/nuavu-today/map.json?v='+Date.now())).json()).map(p=>p.code));
    let prods=[]; for(let off=0;off<10000;off+=100){ const j=await (await fetch('/api/v2/admin/products?display=T&limit=100&offset='+off+'&fields=product_no,product_code,product_name',{headers:H})).json(); const ps=j.products||[]; prods=prods.concat(ps); if(ps.length<100) break; await sleep(200); }
    const missing=prods.filter(p=>!known.has(p.product_code));
    const out=[];
    for(const p of missing){ const j=await (await fetch('/api/v2/admin/products/'+p.product_no+'/options',{headers:H})).json(); const os=(j.option&&j.option.options)||[];
      let combos=['']; for(const o of os){ const vals=(o.option_value||[]).map(v=>v.option_text); combos=combos.flatMap(c=>vals.map(v=>c?c+'-'+v:v)); }
      if(!os.length) combos=[];
      out.push({code:p.product_code,name:p.product_name,opts:combos}); await sleep(350); }
    const blob=new Blob([JSON.stringify(out)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='new_products.json'; document.body.appendChild(a); a.click();
    window.__map={done:true,displayed:prods.length,missing:missing.length,added:out.length};
  }catch(e){ window.__map={done:true,err:String(e)}; }
})();
