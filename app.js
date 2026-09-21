const DATA={
  federal:"data/generated/candidates-federal.json",
  estadual:"data/generated/candidates-estadual.json",
  meta:"data/generated/meta.json",
  chamber:"data/generated/federal-chamber.json",
  topics:"data/reference/policy-topics.json"
};

const PAGE_SIZE=12;
const $=id=>document.getElementById(id);
const esc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));
const norm=value=>String(value||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-zA-Z0-9 ]/g," ").replace(/\s+/g," ").trim().toUpperCase();
const initials=name=>String(name||"?").trim().split(/\s+/).slice(0,2).map(part=>part[0]||"").join("").toUpperCase();
const params=()=>new URLSearchParams(location.search);

async function getJSON(path,fallback=[]){
  try{
    const response=await fetch(path+"?v=5.5",{cache:"no-store"});
    return response.ok?await response.json():fallback;
  }catch{
    return fallback;
  }
}

let TOPICS={version:"0",topics:[]};

async function loadTopics(){
  if(TOPICS.topics.length)return TOPICS;
  TOPICS=await getJSON(DATA.topics,{version:"0",topics:[]});
  return TOPICS;
}

function topicById(id){
  return TOPICS.topics.find(topic=>topic.id===id)||null;
}

function candidateTopicIds(candidate){
  return [...new Set(topicEvidence(candidate).map(item=>item.topic_id).filter(Boolean))];
}

function topicEvidence(candidate){
  return Array.isArray(candidate?.topic_evidence)?candidate.topic_evidence:[];
}

function hasInstitutional(candidate){
  return Boolean(candidate?.current_mandate||(candidate?.institutional_evidence||[]).length);
}

function currentActivity(candidate,kind){
  if(candidate?.current_mandate){
    return kind==="federal"?"Deputado federal em exercício":"Mandato atual confirmado";
  }
  if(candidate?.occupation)return `Trabalho informado ao TSE: ${candidate.occupation}`;
  return "Atuação atual ainda não confirmada nesta base";
}

function practicalAreas(candidate){
  const ids=[...new Set(topicEvidence(candidate).map(item=>item.topic_id).filter(Boolean))];
  return ids.map(id=>topicById(id)).filter(Boolean);
}
function formatSnapshot(iso){
  if(!iso)return "data não disponível";
  try{
    return new Intl.DateTimeFormat("pt-BR",{
      timeZone:"America/Sao_Paulo",
      day:"2-digit",
      month:"2-digit",
      year:"numeric",
      hour:"2-digit",
      minute:"2-digit"
    }).format(new Date(iso));
  }catch{
    return new Date(iso).toLocaleString("pt-BR");
  }
}

async function loadCore(){
  const[federal,estadual,meta]=await Promise.all([
    getJSON(DATA.federal),
    getJSON(DATA.estadual),
    getJSON(DATA.meta,{})
  ]);

  return{
    federal,
    estadual,
    meta,
    all:[
      ...federal.map(item=>({...item,_kind:"federal"})),
      ...estadual.map(item=>({...item,_kind:"estadual"}))
    ]
  };
}

function applyGlobalMeta(meta){
  const stamp=formatSnapshot(meta?.collected_at);
  document.querySelectorAll("[data-snapshot-date]").forEach(node=>node.textContent=stamp);

  const source=meta?.sources?.primary_tse_dataset;
  if(source){
    document.querySelectorAll("[data-tse-source]").forEach(link=>link.href=source);
  }
}

function setupNavigation(){
  const drawer=$("drawer");
  const backdrop=$("backdrop");
  const menuButton=$("menuButton");
  const closeButton=$("closeMenu");

  const syncBackdrop=()=>{
    if(backdrop)backdrop.hidden=!drawer?.classList.contains("open");
  };

  const open=()=>{
    if(!drawer)return;
    drawer.removeAttribute("inert");
    drawer.setAttribute("aria-hidden","false");
    drawer.classList.add("open");
    menuButton?.setAttribute("aria-expanded","true");
    document.body.classList.add("page-lock");
    syncBackdrop();
    closeButton?.focus();
  };

  const close=()=>{
    if(!drawer)return;
    const wasOpen=drawer.classList.contains("open");
    if(wasOpen)menuButton?.focus();
    drawer.classList.remove("open");
    drawer.setAttribute("inert","");
    drawer.setAttribute("aria-hidden","true");
    menuButton?.setAttribute("aria-expanded","false");
    document.body.classList.remove("page-lock");
    syncBackdrop();
  };

  menuButton?.addEventListener("click",open);
  closeButton?.addEventListener("click",close);
  backdrop?.addEventListener("click",close);
  document.addEventListener("keydown",event=>{if(event.key==="Escape")close()});
}

function setupTextSize(){
  const stored=localStorage.getItem("qv_text_scale");
  if(stored==="large")document.documentElement.dataset.scale="large";

  const button=$("textSizeButton");
  if(!button)return;

  const refresh=()=>{
    const large=document.documentElement.dataset.scale==="large";
    button.textContent=large?"A":"A+";
    button.setAttribute("aria-label",large?"Voltar ao tamanho normal do texto":"Aumentar tamanho do texto");
  };

  button.addEventListener("click",()=>{
    const large=document.documentElement.dataset.scale==="large";

    if(large){
      delete document.documentElement.dataset.scale;
      localStorage.removeItem("qv_text_scale");
    }else{
      document.documentElement.dataset.scale="large";
      localStorage.setItem("qv_text_scale","large");
    }
    refresh();
  });

  refresh();
}

function photoSource(candidate){
  return candidate.photo_url||candidate.photoUrl||candidate.foto_url||candidate.photo?.url||"";
}

function photoMarkup(candidate,profile=false){
  const source=photoSource(candidate);
  const name=candidate.ballot_name||candidate.full_name||"candidato";
  const fallback=esc(initials(name));
  const fallbackClass=profile?"profile-photo profile-fallback":"photo-fallback";

  if(!source)return `<div class="${fallbackClass}">Imagem não disponível</div>`;

  const imageClass=profile?' class="profile-photo"':"";
  return `<img${imageClass} src="${esc(source)}" alt="Foto de ${esc(name)}" loading="${profile?"eager":"lazy"}" onerror="this.outerHTML='<div class=&quot;${fallbackClass}&quot;>Imagem não disponível</div>'">`;
}

function getCompareIds(){
  try{
    return JSON.parse(localStorage.getItem("qv_compare")||"[]").map(String).slice(0,3);
  }catch{
    return [];
  }
}

function setCompareIds(ids){
  localStorage.setItem("qv_compare",JSON.stringify([...new Set(ids.map(String))].slice(0,3)));
}

function toggleCompare(id){
  const key=String(id);
  const ids=getCompareIds();
  const index=ids.indexOf(key);

  if(index>=0)ids.splice(index,1);
  else if(ids.length<3)ids.push(key);

  setCompareIds(ids);
  return ids;
}

async function initHome(){
  const[{federal,estadual,meta,all},topics]=await Promise.all([loadCore(),loadTopics()]);
  TOPICS=topics;
  applyGlobalMeta(meta);

  const homeFederalCount=$("homeFederalCount");
  const homeEstadualCount=$("homeEstadualCount");
  const homeTotalCount=$("homeTotalCount");
  if(homeFederalCount)homeFederalCount.textContent=federal.length||"—";
  if(homeEstadualCount)homeEstadualCount.textContent=estadual.length||"—";
  if(homeTotalCount)homeTotalCount.textContent=(federal.length+estadual.length)||"—";

  const evidencedTopicIds=new Set(all.flatMap(candidate=>candidateTopicIds(candidate)));
  const visibleTopics=TOPICS.topics.filter(topic=>evidencedTopicIds.has(topic.id));
  const mount=$("homeTopics");
  if(mount){
    const section=mount.closest(".home-topics");
    if(!visibleTopics.length){
      if(section)section.hidden=true;
      mount.innerHTML="";
    }else{
      if(section)section.hidden=false;
      mount.innerHTML=visibleTopics.map(topic=>`
        <a href="temas.html#${encodeURIComponent(topic.id)}">
          <span>${esc(topic.label)}</span>
          <small>${esc((topic.life_areas||[]).slice(0,2).join(" · "))}</small>
        </a>
      `).join("");
    }
  }
}

function candidateCard(candidate,kind,selectedIds){
  const name=candidate.ballot_name||candidate.full_name||"Nome não disponível";
  const selected=selectedIds.includes(String(candidate.tse_id));
  const profileUrl=`candidato.html?id=${encodeURIComponent(candidate.tse_id)}&cargo=${kind}`;
  const evidence=topicEvidence(candidate);
  const proposalCount=evidence.length;
  const today=currentActivity(candidate,kind);
  const documentedTopics=candidateTopicIds(candidate)
    .map(id=>topicById(id))
    .filter(Boolean);
  const visibleTopics=documentedTopics.slice(0,3);
  const remainingTopics=Math.max(0,documentedTopics.length-visibleTopics.length);
  const topicTags=visibleTopics.length
    ? `<div class="candidate-topic-tags" aria-label="Temas com evidência documentada">${visibleTopics.map(topic=>`<span>${esc(topic.label)}</span>`).join("")}${remainingTopics?`<span class="more">+${remainingTopics}</span>`:""}</div>`
    : "";

  return `
    <article class="candidate-card" data-profile-url="${profileUrl}">
      <a class="candidate-photo-link" href="${profileUrl}" aria-label="Entender candidatura de ${esc(name)}">
        <div class="candidate-photo">${photoMarkup(candidate)}</div>
      </a>
      <div class="candidate-body">
        <p class="candidate-kicker">${kind==="federal"?"DEPUTADO FEDERAL":"DEPUTADO ESTADUAL"}</p>
        <h3><a href="${profileUrl}">${esc(name)}</a></h3>
        <p class="candidate-electoral">${esc(candidate.party||"Partido não informado")} · nº ${esc(candidate.number||"—")}</p>
        <p class="candidate-now">${esc(today)}</p>
        ${topicTags}
        ${proposalCount?`<p class="candidate-proposals">${proposalCount} registro${proposalCount===1?"":"s"} temático${proposalCount===1?"":"s"} com fonte</p>`:""}
      </div>
      <div class="candidate-actions">
        <a class="profile-link" href="${profileUrl}">Entender</a>
        <button class="compare-button${selected?" selected":""}" data-compare-id="${esc(candidate.tse_id)}" type="button">
          ${selected?"Remover":"Comparar"}
        </button>
      </div>
    </article>
  `;
}
function renderPagination(total,page,onPage){
  const mount=$("pagination");
  if(!mount)return;

  const pages=Math.max(1,Math.ceil(total/PAGE_SIZE));

  if(pages<=1){
    mount.innerHTML="";
    return;
  }

  const visible=[];
  for(let current=1;current<=pages;current++){
    if(current===1||current===pages||Math.abs(current-page)<=2)visible.push(current);
  }

  const parts=[
    `<button type="button" data-page="${page-1}" ${page===1?"disabled":""}>Anterior</button>`
  ];

  let previous=0;
  visible.forEach(current=>{
    if(previous&&current-previous>1)parts.push("<span aria-hidden=\"true\">…</span>");
    parts.push(`<button type="button" data-page="${current}" class="${current===page?"active":""}" ${current===page?'aria-current="page"':""}>${current}</button>`);
    previous=current;
  });

  parts.push(`<button type="button" data-page="${page+1}" ${page===pages?"disabled":""}>Próxima</button>`);
  mount.innerHTML=parts.join("");

  mount.querySelectorAll("button[data-page]").forEach(button=>{
    button.addEventListener("click",()=>{
      const next=Number(button.dataset.page);
      if(next>=1&&next<=pages)onPage(next);
    });
  });
}

function updateCompareTray(){
  const tray=$("compareTray");
  if(!tray)return;

  const ids=getCompareIds();
  tray.hidden=!ids.length;
  $("compareCount").textContent=`${ids.length} selecionado${ids.length===1?"":"s"}`;
  $("openCompare").href=`comparar.html?ids=${encodeURIComponent(ids.join(","))}`;
}

async function initCandidates(){
  const[{federal,estadual,meta},topics]=await Promise.all([loadCore(),loadTopics()]);
  TOPICS=topics;
  applyGlobalMeta(meta);

  const datasets={federal,estadual};
  const url=params();
  let kind=url.get("cargo")==="estadual"?"estadual":"federal";
  let page=Math.max(1,Number(url.get("page"))||1);

  $("searchInput").value=url.get("q")||"";
  $("institutionalFilter").value=url.get("institucional")==="1"?"1":"";
  $("federalCount").textContent=federal.length;
  $("estadualCount").textContent=estadual.length;
  $("listUpdate").textContent=`Atualizado em ${formatSnapshot(meta?.collected_at)}`;

  function populateTopics(){
    const select=$("topicFilter");
    const requested=url.get("tema")||select.value;
    const availableIds=new Set(datasets[kind].flatMap(candidate=>candidateTopicIds(candidate)));
    const topicsForKind=TOPICS.topics.filter(topic=>availableIds.has(topic.id));
    select.innerHTML='<option value="">Todos os assuntos com fonte</option>'+
      topicsForKind.map(topic=>`<option value="${esc(topic.id)}">${esc(topic.label)}</option>`).join("");
    select.value=topicsForKind.some(topic=>topic.id===requested)?requested:"";
  }

  const filterToggle=$("filterToggle");
  const secondaryFilters=$("secondaryFilters");
  const activeFilterCount=$("activeFilterCount");
  function updateFilterDisclosure(){
    const count=[$("partyFilter").value,$("topicFilter").value,$("institutionalFilter").value].filter(Boolean).length;
    activeFilterCount.textContent=count?`(${count})`:"";
    if(count&&secondaryFilters.hidden){ secondaryFilters.hidden=false; filterToggle.setAttribute("aria-expanded","true"); }
  }
  filterToggle?.addEventListener("click",()=>{
    secondaryFilters.hidden=!secondaryFilters.hidden;
    filterToggle.setAttribute("aria-expanded",String(!secondaryFilters.hidden));
  });

  function populateParties(){
    const select=$("partyFilter");
    const requested=url.get("partido")||select.value;
    const parties=[...new Set(datasets[kind].map(item=>item.party).filter(Boolean))].sort();

    select.innerHTML='<option value="">Todos os partidos</option>'+
      parties.map(party=>`<option value="${esc(party)}">${esc(party)}</option>`).join("");

    if(parties.includes(requested))select.value=requested;
  }

  function activeFilters(){
    return{
      query:norm($("searchInput").value),
      party:$("partyFilter").value,
      topic:$("topicFilter").value,
      institutional:$("institutionalFilter").value==="1"
    };
  }

  function filteredRows(){
    const filters=activeFilters();

    return datasets[kind]
      .filter(candidate=>{
        const searchable=norm([
          candidate.ballot_name,
          candidate.full_name,
          candidate.number,
          candidate.party,
          candidate.occupation
        ].join(" "));

        if(filters.query&&!searchable.includes(filters.query))return false;
        if(filters.party&&candidate.party!==filters.party)return false;
        if(filters.topic&&!candidateTopicIds(candidate).includes(filters.topic))return false;
        if(filters.institutional&&!hasInstitutional(candidate))return false;
        return true;
      })
      .sort((a,b)=>(a.ballot_name||a.full_name||"").localeCompare(b.ballot_name||b.full_name||"","pt-BR"));
  }

  function syncUrl(){
    const filters=activeFilters();
    const next=new URL(location.href);

    next.searchParams.set("cargo",kind);
    next.searchParams.set("page",String(page));

    const query=$("searchInput").value.trim();
    query?next.searchParams.set("q",query):next.searchParams.delete("q");
    filters.party?next.searchParams.set("partido",filters.party):next.searchParams.delete("partido");
    filters.topic?next.searchParams.set("tema",filters.topic):next.searchParams.delete("tema");
    filters.institutional?next.searchParams.set("institucional","1"):next.searchParams.delete("institucional");

    history.replaceState(null,"",next);
  }

  function render(){
    const rows=filteredRows();
    const pages=Math.max(1,Math.ceil(rows.length/PAGE_SIZE));
    if(page>pages)page=pages;

    const start=(page-1)*PAGE_SIZE;
    const visible=rows.slice(start,start+PAGE_SIZE);
    const selected=getCompareIds();

    $("resultCount").textContent=`${rows.length} pessoa${rows.length===1?"":"s"}`;
    $("pageStatus").textContent=rows.length?`Página ${page} de ${pages}`:"Nenhum resultado";
    $("cards").innerHTML=visible.length
      ? visible.map(candidate=>candidateCard(candidate,kind,selected)).join("")
      : `<div class="empty">${activeFilters().topic?"Ainda não encontramos fala, proposta ou atuação com fonte para este assunto e cargo. Isso não significa que a pessoa não tenha posição.":"Ninguém encontrado com esses filtros."}</div>`;

    $("cards").querySelectorAll(".candidate-card[data-profile-url]").forEach(card=>{
      const open=()=>location.href=card.dataset.profileUrl;
      card.addEventListener("click",event=>{ if(!event.target.closest("a,button"))open(); });
      
    });

        $("cards").querySelectorAll("[data-compare-id]").forEach(button=>{
      button.addEventListener("click",()=>{
        toggleCompare(button.dataset.compareId);
        render();
      });
    });

    renderPagination(rows.length,page,nextPage=>{
      page=nextPage;
      render();
      window.scrollTo({top:document.querySelector(".results-head").offsetTop-100,behavior:"smooth"});
    });

    updateCompareTray();
    syncUrl();
  }

  function setKind(nextKind){
    kind=nextKind;
    page=1;

    document.querySelectorAll(".office-button").forEach(button=>{
      const active=button.dataset.kind===kind;
      button.classList.toggle("active",active);
      button.setAttribute("aria-selected",String(active));
    });

    populateTopics();
    populateParties();
    render();
  }

  const rerender=()=>{
    page=1;
    render();
  };

  document.querySelectorAll(".office-button").forEach(button=>{
    button.addEventListener("click",()=>setKind(button.dataset.kind));
  });

  $("searchInput").addEventListener("input",rerender);
  $("partyFilter").addEventListener("change",rerender);
  $("topicFilter").addEventListener("change",rerender);
  $("institutionalFilter").addEventListener("change",rerender);

  $("clearFilters").addEventListener("click",()=>{
    $("searchInput").value="";
    $("partyFilter").value="";
    $("topicFilter").value="";
    $("institutionalFilter").value="";
    page=1;
    render();
  });

  $("clearCompare").addEventListener("click",()=>{
    setCompareIds([]);
    render();
  });

  populateParties();
  setKind(kind);
}

async function initTopics(){
  return Promise.all([loadCore(),loadTopics()]).then(([core,topics])=>{
    TOPICS=topics;
    applyGlobalMeta(core.meta);
    const stats={};
    TOPICS.topics.forEach(topic=>stats[topic.id]={candidates:new Set(),evidence:0});
    core.all.forEach(candidate=>topicEvidence(candidate).forEach(item=>{
      if(stats[item.topic_id]){
        stats[item.topic_id].candidates.add(String(candidate.tse_id));
        stats[item.topic_id].evidence+=1;
      }
    }));
    const visibleTopics=TOPICS.topics.filter(topic=>stats[topic.id]?.candidates.size);
    $("topicCards").innerHTML=visibleTopics.length?visibleTopics.map(topic=>{
      const row=stats[topic.id];
      const count=row.candidates.size;
      return `
        <article class="topic-row" id="${esc(topic.id)}">
          <div class="topic-main">
            <h2>${esc(topic.label)}</h2>
            <p>${esc(topic.description)}</p>
            <div class="life-areas">${(topic.life_areas||[]).map(area=>`<span>${esc(area)}</span>`).join("")}</div>
          </div>
          <div class="topic-status">
            <strong>${count}</strong>
            <span>pessoa${count===1?"":"s"} com fonte neste assunto</span>
          </div>
          <a href="candidatos.html?tema=${encodeURIComponent(topic.id)}">Ver pessoas</a>
        </article>
      `;
    }).join(""):'<div class="empty">Ainda não há propostas, declarações ou atuações temáticas integradas com fonte. A ausência de registro não significa ausência de posição.</div>';
  });
}
function registrationStatusLabel(value){
  const normalized=String(value||"").trim().toLowerCase();
  if(!normalized||normalized==="not_available"){
    return "Ainda não disponível na fonte atual";
  }
  return value;
}

function definitionRow(label,value){
  return `<div class="definition-row"><dt>${esc(label)}</dt><dd>${esc(value||"Não disponível")}</dd></div>`;
}

function historicalList(items,mapper){
  return items?.length
    ? `<div class="timeline-list">${items.map(mapper).join("")}</div>`
    : '<div class="evidence-empty">Ainda não disponível nesta base.</div>';
}

function profileSection(id,title,subtitle,content,open=false){
  return `
    <details class="profile-disclosure" id="${id}" ${open?"open":""}>
      <summary>
        <span>${esc(title)}</span>
        <small>${esc(subtitle)}</small>
      </summary>
      <div class="profile-disclosure-body">${content}</div>
    </details>
  `;
}

async function initProfile(){
  const id=params().get("id");
  const requested=params().get("cargo");
  const[{federal,estadual,meta},chamber,topics]=await Promise.all([loadCore(),getJSON(DATA.chamber),loadTopics()]);
  applyGlobalMeta(meta); TOPICS=topics;

  if(!id){ $("profileMount").className="empty"; $("profileMount").innerHTML="Pessoa não informada."; return; }
  const all=[...federal.map(item=>({...item,_kind:"federal"})),...estadual.map(item=>({...item,_kind:"estadual"}))];
  const candidate=all.find(item=>String(item.tse_id)===String(id));
  if(!candidate){ $("profileMount").className="empty"; $("profileMount").innerHTML="Pessoa não encontrada na base atual."; return; }

  const kind=candidate._kind||requested||"federal";
  const name=candidate.ballot_name||candidate.full_name||"Candidato";
  const institutional=candidate.current_mandate||null;
  const chamberRow=kind==="federal"?chamber.find(item=>String(item.candidate_id||item.tse_id||"")===String(id))||null:null;
  const historyItems=candidate.previous_elections||[];
  const institutionalEvidence=candidate.institutional_evidence||[];
  const thematicEvidence=topicEvidence(candidate);
  const impactTopics=practicalAreas(candidate);
  const socialName=candidate.social_name&&norm(candidate.social_name)!==norm(name)?candidate.social_name:null;
  const organization=(
    candidate.coalition&&norm(candidate.coalition)!=="PARTIDO ISOLADO"
      ? candidate.coalition_composition||candidate.coalition
      : candidate.coalition
        ? "Partido isolado"
        : null
  );
  const electoralFacts=[
    {
      label:"Partido",
      value:candidate.party_name
        ? [candidate.party,candidate.party_name].filter(Boolean).join(" · ")
        : candidate.party
    },
    {label:"Federação / composição",value:organization},
    {label:"Escolaridade",value:candidate.education},
    {label:"Ocupação declarada",value:candidate.occupation},
    {label:"Situação da candidatura",value:registrationStatusLabel(candidate.registration_status)},
    {label:"Situação de totalização",value:candidate.totalization_status}
  ].filter(item=>item.value);
  const electoralFactsContent=electoralFacts.length?`
    <div class="electoral-data" aria-label="Dados eleitorais do TSE">
      <div class="electoral-data-head">
        <strong>Dados eleitorais do TSE</strong>
        <span>Cadastro de candidaturas · 2026</span>
      </div>
      <dl class="electoral-data-grid">
        ${electoralFacts.map(item=>`<div class="electoral-data-item"><dt>${esc(item.label)}</dt><dd>${esc(item.value)}</dd></div>`).join("")}
      </dl>
    </div>
  `:"";

  document.title=`${name} · Quem Votar?`;
  const roleLabel=kind==="federal"?"Deputado Federal":"Deputado Estadual";
  const shareDescription=`${name} · ${roleLabel} · ${candidate.party||"Partido não informado"} · nº ${candidate.number||"—"}. Consulte dados públicos e fontes.`;
  const profileUrl=new URL(location.href);
  profileUrl.searchParams.set("id",String(candidate.tse_id));
  profileUrl.searchParams.set("cargo",kind);
  const canonicalUrl=profileUrl.toString();
  document.querySelector('meta[property="og:title"]')?.setAttribute("content",document.title);
  document.querySelector('meta[property="og:description"]')?.setAttribute("content",shareDescription);
  document.querySelector('meta[property="og:url"]')?.setAttribute("content",canonicalUrl);
  document.querySelector('meta[name="twitter:title"]')?.setAttribute("content",document.title);
  document.querySelector('meta[name="twitter:description"]')?.setAttribute("content",shareDescription);
  document.querySelector('link[rel="canonical"]')?.setAttribute("href",canonicalUrl);

  const todayContent=institutional||institutionalEvidence.length?`
    ${institutional?`<div class="plain-fact"><span>Hoje</span><strong>${esc(currentActivity(candidate,kind))}</strong><small>${esc([institutional.party,institutional.status].filter(Boolean).join(" · "))}</small></div>`:""}
    ${institutionalEvidence.length?`<div class="public-records">${institutionalEvidence.map(item=>`<article><span>${esc(item.reference_date||"Data não informada")}</span><strong>${esc(item.institution||"Órgão público")}</strong><p>${esc([item.legislature,item.type].filter(Boolean).join(" · "))}</p>${item.source?.url?`<a target="_blank" rel="noopener" href="${esc(item.source.url)}">Abrir fonte</a>`:""}</article>`).join("")}</div>`:""}
  `:`<p class="plain-empty">Não encontramos atuação pública atual confirmada nesta base. Isso não significa que ela não exista.</p>`;

  const promisesContent=thematicEvidence.length?`<div class="promise-list">${thematicEvidence.map(item=>{
      const topic=topicById(item.topic_id);
      return `<article><span>${esc(topic?.label||item.topic_id||"Assunto")}</span><h3>${esc(item.quote_or_summary||item.statement||"Declaração documentada")}</h3><p>${esc(item.evidence_type||"Fonte documentada")}</p>${item.source_url?`<a target="_blank" rel="noopener" href="${esc(item.source_url)}">Ver fonte</a>`:""}</article>`;
    }).join("")}</div>`:`<div class="plain-empty"><strong>Ainda não coletamos uma proposta ou declaração de campanha desta pessoa.</strong><p>Não vamos adivinhar posição pelo partido, profissão ou histórico.</p></div>`;

  const impactContent=impactTopics.length?`<div class="impact-list">${impactTopics.map(topic=>`<article><h3>${esc(topic.practical_question||topic.label)}</h3><div class="life-areas">${(topic.life_areas||[]).map(area=>`<span>${esc(area)}</span>`).join("")}</div></article>`).join("")}</div><p class="impact-note">Essas são áreas que a proposta pode atingir. O site não classifica o efeito como bom ou ruim para você.</p>`:`<div class="plain-empty"><strong>Sem proposta ou declaração documentada, não dá para afirmar impacto específico.</strong><p>Quando houver fonte, esta área mostra onde o assunto pode aparecer na vida real.</p></div>`;

  const historyContent=historyItems.length?`<div class="timeline-list">${historyItems.map(item=>`<div class="timeline-item"><strong>${esc(item.year||"Data não disponível")}</strong><div>${esc(item.office||"Cargo")}<small>${esc([item.party,item.location,item.result].filter(Boolean).join(" · "))}</small></div></div>`).join("")}</div>`:`<p class="plain-empty">Histórico eleitoral detalhado ainda não está disponível nesta base.</p>`;

  const sources=[
    candidate.source?.official_portal?{name:"TSE · cadastro eleitoral",detail:`Atualizado em ${formatSnapshot(meta?.collected_at)}`,url:candidate.source.official_portal}:null,
    candidate.photo_source?.official_archive_url?{name:"TSE · foto",detail:candidate.photo_source.dataset||"Arquivo oficial",url:candidate.photo_source.official_archive_url}:null,
    (candidate.current_mandate?.profile_url||chamberRow?.profile_url)?{name:"Câmara dos Deputados",detail:"Perfil público",url:candidate.current_mandate?.profile_url||chamberRow?.profile_url}:null,
    ...institutionalEvidence.filter(item=>item.source?.url).map(item=>({name:item.institution||"Fonte pública",detail:item.reference_date||"",url:item.source.url})),
    ...thematicEvidence.filter(item=>item.source_url).map(item=>({name:topicById(item.topic_id)?.label||"Proposta/declaração",detail:item.source_publisher||item.published_at||"",url:item.source_url}))
  ].filter(Boolean);

  $("profileMount").className="";
  $("profileMount").innerHTML=`
    <a class="back-link" href="candidatos.html?cargo=${kind}">Voltar para pessoas</a>
    <section class="profile-hero">
      <div class="profile-photo-wrap">${photoMarkup(candidate,true)}</div>
      <div class="profile-copy">
        <p class="eyebrow">${kind==="federal"?"DEPUTADO FEDERAL":"DEPUTADO ESTADUAL"} · ESPÍRITO SANTO</p>
        <h1>${esc(name)}</h1>
        <p class="full-name">${esc(candidate.full_name||"")}</p>
        ${socialName?`<p class="social-name">Nome social: ${esc(socialName)}</p>`:""}
        <div class="identity-line"><strong>${esc(candidate.party||"Partido não informado")}</strong><span>nº ${esc(candidate.number||"—")}</span></div>
        ${electoralFactsContent}
        <div class="profile-actions">
          <button id="profileCompare" class="profile-compare" type="button" data-candidate-id="${esc(candidate.tse_id)}">${getCompareIds().includes(String(candidate.tse_id))?"Remover da comparação":"Comparar"}</button>
          <button id="profileShare" class="profile-share" type="button">Compartilhar perfil</button>
        </div>
      </div>
    </section>

    <nav class="profile-jump" aria-label="Ir para uma pergunta">
      <a href="#faz-hoje">O que faz hoje?</a><a href="#vai-fazer">O que diz que vai fazer?</a><a href="#impacto">Onde isso mexe?</a><a href="#historico">Histórico</a><a href="#fontes">Fontes</a>
    </nav>

    <section class="answer-section" id="faz-hoje"><p class="section-number">01</p><div><h2>O que essa pessoa faz hoje?</h2>${todayContent}</div></section>
    <section class="answer-section" id="vai-fazer"><p class="section-number">02</p><div><h2>O que ela diz que vai fazer?</h2>${promisesContent}</div></section>
    <section class="answer-section impact-section" id="impacto"><p class="section-number">03</p><div><h2>Onde isso pode mexer na vida real?</h2>${impactContent}</div></section>
    <section class="answer-section secondary-answer" id="historico"><p class="section-number">04</p><div><h2>Histórico</h2>${historyContent}</div></section>
    <section class="answer-section secondary-answer" id="fontes"><p class="section-number">05</p><div><h2>De onde saiu isso?</h2><div class="source-list">${sources.map(s=>`<div class="source-item"><div><strong>${esc(s.name)}</strong><span>${esc(s.detail)}</span></div><a target="_blank" rel="noopener" href="${esc(s.url)}">Abrir</a></div>`).join("")||'<p class="plain-empty">Nenhuma fonte adicional disponível.</p>'}</div></div></section>
  `;

  $("profileCompare")?.addEventListener("click",event=>{
    const ids=toggleCompare(event.currentTarget.dataset.candidateId);
    event.currentTarget.textContent=ids.includes(String(candidate.tse_id))?"Remover da comparação":"Comparar";
  });

  $("profileShare")?.addEventListener("click",async event=>{
    const button=event.currentTarget;
    const original=button.textContent;
    try{
      if(navigator.share){
        await navigator.share({title:document.title,text:shareDescription,url:canonicalUrl});
        return;
      }
      await navigator.clipboard.writeText(canonicalUrl);
      button.textContent="Link copiado";
      setTimeout(()=>button.textContent=original,1800);
    }catch(error){
      if(error?.name==="AbortError")return;
      button.textContent="Copie o link da barra";
      setTimeout(()=>button.textContent=original,2200);
    }
  });
}
async function initCompare(){
  const[{all,meta},topics]=await Promise.all([loadCore(),loadTopics()]);
  TOPICS=topics;
  applyGlobalMeta(meta);

  const fromUrl=(params().get("ids")||"").split(",").filter(Boolean).map(String);
  const ids=(fromUrl.length?fromUrl:getCompareIds()).slice(0,3);
  const selected=ids.map(id=>all.find(candidate=>String(candidate.tse_id)===id)).filter(Boolean);

  if(!selected.length){
    $("compareMount").innerHTML=`
      <div class="compare-empty">
        <h2>Ninguém selecionado.</h2>
        <p>Abra a lista e escolha até três pessoas para comparar.</p>
        <a href="candidatos.html?cargo=federal">Escolher pessoas</a>
      </div>
    `;
    return;
  }

  setCompareIds(ids);

  const columns=selected.length;
  const row=(label,renderer)=>`
    <div class="row-label">${esc(label)}</div>
    ${selected.map(renderer).join("")}
  `;

  $("compareMount").innerHTML=`
    <div class="comparison-wrap">
      <div class="comparison-grid" style="--compare-cols:${columns}">
        <div class="row-label">Candidato</div>
        ${selected.map(candidate=>`
          <div class="compare-person">
            ${photoMarkup(candidate,true)}
            <h2>${esc(candidate.ballot_name||candidate.full_name)}</h2>
            <span>${esc(candidate.party||"—")} · Nº ${esc(candidate.number||"—")}</span>
            <br>
            <a href="candidato.html?id=${encodeURIComponent(candidate.tse_id)}&cargo=${candidate._kind}">Abrir perfil</a>
          </div>
        `).join("")}

        ${row("Cargo",candidate=>`<div class="compare-value">${candidate._kind==="federal"?"Deputado Federal":"Deputado Estadual"}</div>`)}
        ${row("Hoje",candidate=>`<div class="compare-value">${esc(currentActivity(candidate,candidate._kind))}</div>`)}
                ${row("Escolaridade",candidate=>`<div class="compare-value">${esc(candidate.education||"Não disponível")}</div>`)}
        ${row("Atuação pública",candidate=>`<div class="compare-value">${hasInstitutional(candidate)?"Há informação pública disponível":"Ainda não encontramos atuação pública atual"}</div>`)}
        ${row("O que diz que vai fazer",candidate=>`<div class="compare-value">${topicEvidence(candidate).length?practicalAreas(candidate).map(t=>esc(t.label)).join(" · "):"Ainda sem proposta ou declaração com fonte"}</div>`)}
      </div>
    </div>
    <p class="comparison-note">Dados disponíveis em ${esc(formatSnapshot(meta?.collected_at))}. Falta de informação aqui não significa ausência de proposta, posição ou experiência.</p>
  `;
}

async function initAbout(){
  const{meta}=await loadCore();
  applyGlobalMeta(meta);

  if($("aboutUpdate")){
    $("aboutUpdate").textContent=formatSnapshot(meta?.collected_at);
  }
}

setupNavigation();
setupTextSize();

const page=document.body.dataset.page;
if(page==="home")initHome();
if(page==="candidates")initCandidates();
if(page==="topics")initTopics();
if(page==="profile")initProfile();
if(page==="compare")initCompare();
if(page==="about")initAbout();
