(function(){
  'use strict';
  const STORAGE_KEY='qv_compare';
  const MAX=3;
  const page=document.body?.dataset?.page||'';

  function unique(ids){
    return [...new Set((ids||[]).map(String).map(v=>v.trim()).filter(Boolean))];
  }
  function normalize(ids,valid){
    return unique(ids).filter(id=>!valid||valid.has(id)).slice(0,MAX);
  }
  function read(){
    try{return unique(JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]'));}catch{return [];}
  }
  function write(ids){localStorage.setItem(STORAGE_KEY,JSON.stringify(normalize(ids,window.__qvValidCompareIds)));}
  function announce(text){
    const live=document.getElementById('compareStatus');
    if(live)live.textContent=text;
  }
  function syncA11y(){
    const ids=normalize(read(),window.__qvValidCompareIds);
    if(JSON.stringify(ids)!==JSON.stringify(read()))write(ids);
    document.querySelectorAll('[data-compare-id]').forEach(button=>{
      const selected=ids.includes(String(button.dataset.compareId));
      button.setAttribute('aria-pressed',String(selected));
      button.setAttribute('aria-disabled',String(!selected&&ids.length>=MAX));
      if(!selected&&ids.length>=MAX)button.setAttribute('aria-label','Limite de 3 candidaturas atingido. Remova uma seleção para escolher esta pessoa.');
      else button.removeAttribute('aria-label');
    });
    const profile=document.getElementById('profileCompare');
    if(profile){
      const selected=ids.includes(String(profile.dataset.candidateId));
      profile.setAttribute('aria-pressed',String(selected));
      profile.setAttribute('aria-disabled',String(!selected&&ids.length>=MAX));
    }
    const open=document.getElementById('openCompare');
    if(open){
      const ready=ids.length>=2;
      open.setAttribute('aria-disabled',String(!ready));
      open.tabIndex=ready?0:-1;
      if(ready){
        open.removeAttribute('data-disabled');
        open.href=`comparar.html?ids=${encodeURIComponent(ids.join(','))}`;
      }else{
        open.setAttribute('data-disabled','true');
        open.removeAttribute('href');
      }
    }
    const count=document.getElementById('compareCount');
    if(count)count.textContent=ids.length===1?'1 selecionado · escolha mais uma pessoa':`${ids.length} selecionados`;
  }
  async function validIds(){
    try{
      const [f,e]=await Promise.all([
        fetch('data/generated/candidates-federal.json?v=5.5',{cache:'no-store'}).then(r=>r.ok?r.json():[]),
        fetch('data/generated/candidates-estadual.json?v=5.5',{cache:'no-store'}).then(r=>r.ok?r.json():[])
      ]);
      return new Set([...f,...e].map(c=>String(c.tse_id)).filter(Boolean));
    }catch{return null;}
  }
  function sanitizeCompareUrl(valid){
    if(page!=='compare')return;
    const url=new URL(location.href);
    const raw=(url.searchParams.get('ids')||'').split(',').filter(Boolean);
    if(!raw.length)return;
    const clean=normalize(raw,valid);
    if(clean.join(',')!==raw.join(',')){
      clean.length?url.searchParams.set('ids',clean.join(',')):url.searchParams.delete('ids');
      history.replaceState(null,'',url);
    }
    write(clean);
  }
  function installGuards(){
    document.addEventListener('click',event=>{
      const button=event.target.closest('[data-compare-id],#profileCompare');
      if(!button)return;
      const id=String(button.dataset.compareId||button.dataset.candidateId||'');
      const ids=normalize(read(),window.__qvValidCompareIds);
      if(!ids.includes(id)&&ids.length>=MAX){
        event.preventDefault();
        event.stopImmediatePropagation();
        announce('Você já selecionou 3 candidaturas. Remova uma para escolher outra.');
        syncA11y();
      }else{
        setTimeout(()=>{syncA11y();announce(ids.includes(id)?'Candidatura removida da comparação.':'Seleção atualizada.');},0);
      }
    },true);
    document.addEventListener('click',event=>{
      const open=event.target.closest('#openCompare[data-disabled="true"]');
      if(!open)return;
      event.preventDefault();
      announce('Escolha pelo menos 2 candidaturas para comparar.');
    },true);
    new MutationObserver(syncA11y).observe(document.body,{childList:true,subtree:true});
  }

  (async()=>{
    window.__qvValidCompareIds=await validIds();
    write(read());
    sanitizeCompareUrl(window.__qvValidCompareIds);
    installGuards();
    setTimeout(syncA11y,0);
  })();
})();
