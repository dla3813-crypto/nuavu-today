// [랭킹 2단계] rank_ids.json(GitHub) → 카페24 API 로 이름·이미지·가격 보강 → ~/Downloads/ranking.json 다운로드
// 크롬 탭 https://nuavu.cafe24api.com/... 에서 javascript_tool 로 실행. 결과: window.__rk = {done, n, err}
(async()=>{
  window.__rk={done:false};
  try{
    let tok=JSON.parse(localStorage.getItem('nv_tok'));
    if(new Date(tok.expires_at+'+09:00')-Date.now()<15*60*1000){ const r=await fetch('/api/v2/oauth/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded','Authorization':'Basic '+btoa(localStorage.getItem('nv_client')+':'+localStorage.getItem('nv_secret'))},body:new URLSearchParams({grant_type:'refresh_token',refresh_token:tok.refresh_token})}); const j=await r.json(); if(j.access_token){localStorage.setItem('nv_tok',JSON.stringify(j)); tok=j;} }
    const H={'Authorization':'Bearer '+tok.access_token}; const sleep=ms=>new Promise(r=>setTimeout(r,ms));
    const ids=await (await fetch('https://dla3813-crypto.github.io/nuavu-today/rank_ids.json?v='+Date.now())).json();
    const nos=ids.map(x=>x.no);
    const pj=await (await fetch('/api/v2/admin/products?product_no='+nos.join(',')+'&limit=100&fields=product_no,product_name,price,list_image,display,selling,sold_out',{headers:H})).json();
    const info={}; (pj.products||[]).forEach(p=>info[p.product_no]=p);
    const items=[];
    for(const x of ids){ const p=info[x.no]; if(!p || p.display!=='T' || p.selling!=='T') continue;
      let sale=null; try{ const d=await (await fetch('/api/v2/admin/products/'+x.no+'/discountprice',{headers:H})).json(); sale=d.discountprice && +d.discountprice.mobile_discount_price; }catch(e){}
      items.push({rank:items.length+1, no:x.no, name:p.product_name, img:p.list_image, price:+p.price, sale:(sale&&sale<+p.price)?sale:null, soldout:p.sold_out==='T'}); await sleep(250); }
    const out={updated:new Date(Date.now()+9*3600e3).toISOString().slice(5,16).replace('T',' ').replace('-','.'), items};
    const blob=new Blob([JSON.stringify(out)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='ranking.json'; document.body.appendChild(a); a.click();
    window.__rk={done:true,n:items.length};
  }catch(e){ window.__rk={done:true,err:String(e)}; }
})();
