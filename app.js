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
    const response=await fetch(path+"?v=5",{cache:"no-store"});
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

  const syncBackdrop=()=>{
    if(backdrop)backdrop.hidden=!drawer?.classList.contains("open");
  };

  const open=()=>{
    drawer?.classList.add("open");
    drawer?.setAttribute("aria-hidden","false");
    $("menuButton")?.setAttribute("aria-expanded","true");
    document.body.classList.add("page-lock");
    syncBackdrop();
  };

  const close=()=>{
    drawer?.classList.remove("open");
    drawer?.setAttribute("aria-hidden","true");
    $("menuButton")?.setAttribute("aria-expanded","false");
    document.body.classList.remove("page-lock");
    syncBackdrop();
  };

  $("menuButton")?.addEventListener("click",open);
  $("closeMenu")?.addEventListener("click",close);
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
  const[{federal,estadual,meta},topics]=await Promise.all([loadCore(),loadTopics()]);
  TOPICS=topics;
  applyGlobalMeta(meta);

  $("homeFederalCount").textContent=federal.length||"—";
  $("homeEstadualCount").textContent=estadual.length||"—";
  $("homeTotalCount").textContent=(federal.length+estadual.length)||"—";

  const mount=$("homeTopics");
  if(mount){
    mount.innerHTML=TOPICS.topics.map(topic=>`
      <a href="temas.html#${encodeURIComponent(topic.id)}">
        <span>${esc(topic.label)}</span>
        <small>Ver tema</small>
      </a>
    `).join("");
  }
}

function candidateCard(candidate,kind,selectedIds){
  const name=candidate.ballot_name||candidate.full_name||"Nome não disponível";
  const selected=selectedIds.includes(String(candidate.tse_id));
  const profileUrl=`candidato.html?id=${encodeURIComponent(candidate.tse_id)}&cargo=${kind}`;
  const evidenceCount=topicEvidence(candidate).length;
  const meta=[
    candidate.occupation?`Ocupação declarada: ${candidate.occupation}`:null,
    hasInstitutional(candidate)?"Registro institucional integrado":null,
    evidenceCount?`${evidenceCount} evidência${evidenceCount===1?"":"s"} temática${evidenceCount===1?"":"s"}`:null
  ].filter(Boolean);

  return `
    <article class="candidate-card" data-profile-url="${profileUrl}">
      <a class="candidate-photo-link" href="${profileUrl}" aria-label="Abrir perfil de ${esc(name)}">
        <div class="candidate-photo">${photoMarkup(candidate)}</div>
      </a>
      <div class="candidate-body">
        <h3><a href="${profileUrl}">${esc(name)}</a></h3>
        <p class="candidate-electoral">${kind==="federal"?"Deputado Federal":"Deputado Estadual"} · ${esc(candidate.party||"Partido não informado")} · nº ${esc(candidate.number||"—")}</p>
        ${meta.length?`<p class="candidate-occupation">${meta.map(esc).join(" · ")}</p>`:""}
      </div>
      <div class="candidate-actions">
        <a class="profile-link" href="${profileUrl}">Ver perfil</a>
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
  $("topicFilter").value=url.get("tema")||"";
  $("institutionalFilter").value=url.get("institucional")==="1"?"1":"";
  $("federalCount").textContent=federal.length;
  $("estadualCount").textContent=estadual.length;
  $("listUpdate").textContent=`Snapshot ${formatSnapshot(meta?.collected_at)}`;
  $("topicFilter").innerHTML='<option value="">Todos os temas documentados</option>'+
    TOPICS.topics.map(topic=>`<option value="${esc(topic.id)}">${esc(topic.label)}</option>`).join("");
  $("topicFilter").value=url.get("tema")||"";

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

    $("resultCount").textContent=`${rows.length} candidatura${rows.length===1?"":"s"}`;
    $("pageStatus").textContent=rows.length?`Página ${page} de ${pages}`:"Nenhum resultado";
    $("cards").innerHTML=visible.length
      ? visible.map(candidate=>candidateCard(candidate,kind,selected)).join("")
      : `<div class="empty">${activeFilters().topic?"Nenhuma evidência temática integrada para este tema e cargo no snapshot atual. Isso não significa ausência de posição do candidato.":"Nenhuma candidatura encontrada com esses filtros."}</div>`;

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
    $("topicCards").innerHTML=TOPICS.topics.map(topic=>{
      const row=stats[topic.id];
      const count=row.candidates.size;
      const evidence=row.evidence;
      return `
        <article class="topic-row" id="${esc(topic.id)}">
          <div>
            <h2>${esc(topic.label)}</h2>
            <p>${esc(topic.description)}</p>
          </div>
          <div class="topic-count">
            <strong>${count?count:"—"}</strong>
            <span>${count?`candidatura${count===1?"":"s"} · ${evidence} evidência${evidence===1?"":"s"}`:"Cobertura ainda não publicada"}</span>
          </div>
          ${count?`<a href="candidatos.html?tema=${encodeURIComponent(topic.id)}">Ver candidaturas</a>`:""}
        </article>
      `;
    }).join("");
  });
}

function definitionRow(label,value){
  return `<div class="definition-row"><dt>${esc(label)}</dt><dd>${esc(value||"Não disponível")}</dd></div>`;
}

function historicalList(items,mapper){
  return items?.length
    ? `<div class="timeline-list">${items.map(mapper).join("")}</div>`
    : '<div class="evidence-empty">Ainda não integrado nesta camada.</div>';
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

  const[{federal,estadual,meta},chamber,topics]=await Promise.all([
    loadCore(),
    getJSON(DATA.chamber),
    loadTopics()
  ]);

  applyGlobalMeta(meta);
  TOPICS=topics;

  if(!id){
    $("profileMount").className="empty";
    $("profileMount").innerHTML="Candidato não informado.";
    return;
  }

  const all=[
    ...federal.map(item=>({...item,_kind:"federal"})),
    ...estadual.map(item=>({...item,_kind:"estadual"}))
  ];

  const candidate=all.find(item=>String(item.tse_id)===String(id));

  if(!candidate){
    $("profileMount").className="empty";
    $("profileMount").innerHTML="Candidato não encontrado no snapshot atual.";
    return;
  }

  const kind=candidate._kind||requested||"federal";
  const name=candidate.ballot_name||candidate.full_name||"Candidato";
  const institutional=candidate.current_mandate||null;
  const chamberRow=kind==="federal"
    ? chamber.find(item=>String(item.candidate_id||item.tse_id||"")===String(id))||null
    : null;
  const historyItems=candidate.previous_elections||[];
  const institutionalEvidence=candidate.institutional_evidence||[];
    const thematicEvidence=topicEvidence(candidate);

  document.title=`${name} · Quem Votar?`;

    const generalContent=`
    <dl class="definition-list">
      ${definitionRow("Nome completo",candidate.full_name)}
      ${definitionRow("Cargo",kind==="federal"?"Deputado Federal":"Deputado Estadual")}
      ${definitionRow("Partido",candidate.party)}
      ${definitionRow("Número",candidate.number)}
      ${definitionRow("Ocupação",candidate.occupation)}
      ${definitionRow("Escolaridade",candidate.education)}
      ${definitionRow("Situação da candidatura",candidate.registration_status||"Ainda não integrada")}
    </dl>
    ${institutional?`
      <div class="subsection">
        <h3>Registro institucional integrado</h3>
        <dl class="definition-list">
          ${definitionRow("Instituição",kind==="federal"?"Câmara dos Deputados":"ALES")}
          ${definitionRow("Partido institucional",institutional.party)}
          ${definitionRow("Situação",institutional.status)}
        </dl>
      </div>
    `:""}
  `;

  const historyContent=`
    <div class="subsection">
      <h3>Histórico eleitoral</h3>
      ${historicalList(historyItems,item=>`
        <div class="timeline-item">
          <strong>${esc(item.year||"Data não disponível")}</strong>
          <div>${esc(item.office||"Cargo")}<small>${esc([item.party,item.location,item.result].filter(Boolean).join(" · "))}</small></div>
        </div>
      `)}
    </div>
    <div class="subsection">
      <h3>Atuação institucional documentada</h3>
      ${historicalList(institutionalEvidence,item=>`
        <div class="timeline-item">
          <strong>${esc(item.reference_date||"Data não informada")}</strong>
          <div>${esc(item.institution||"Instituição")}<small>${esc([item.legislature,item.type].filter(Boolean).join(" · "))}</small></div>
        </div>
      `)}
    </div>
  `;

  const topicsContent=thematicEvidence.length
    ? `<div class="timeline-list">${thematicEvidence.map(item=>`
        <div class="timeline-item">
          <strong>${esc(topicById(item.topic_id)?.label||item.topic_id||"Tema")}</strong>
          <div>
            <b>${esc(item.evidence_type||"Evidência documentada")}</b>
            <small>${esc(item.quote_or_summary||item.statement||"")}</small>
            ${item.source_url?`<a class="plain-link" target="_blank" rel="noopener" href="${esc(item.source_url)}">Abrir fonte</a>`:""}
          </div>
        </div>
      `).join("")}</div>`
    : '<div class="evidence-empty">Esta camada ainda não foi integrada para esta candidatura. Isso não significa ausência de proposta, posição ou atuação.</div>';

  const sourcesContent=`
    <div class="source-list">
      <div class="source-item">
        <div><strong>TSE · Dados Abertos</strong><span>Snapshot ${esc(formatSnapshot(meta?.collected_at))}</span></div>
        ${candidate.source?.official_portal?`<a target="_blank" rel="noopener" href="${esc(candidate.source.official_portal)}">Abrir fonte</a>`:""}
      </div>
      ${candidate.photo_source?.official_archive_url?`
        <div class="source-item">
          <div><strong>TSE · Fotografias</strong><span>${esc(candidate.photo_source.dataset||"Arquivo oficial de fotos")}</span></div>
          <a target="_blank" rel="noopener" href="${esc(candidate.photo_source.official_archive_url)}">Abrir fonte</a>
        </div>
      `:""}
      ${(candidate.current_mandate?.profile_url||chamberRow?.profile_url)?`
        <div class="source-item">
          <div><strong>Câmara dos Deputados</strong><span>Perfil institucional</span></div>
          <a target="_blank" rel="noopener" href="${esc(candidate.current_mandate?.profile_url||chamberRow?.profile_url)}">Abrir fonte</a>
        </div>
      `:""}
      ${institutionalEvidence.map(item=>item.source?.url?`
        <div class="source-item">
          <div><strong>${esc(item.institution||"Fonte institucional")}</strong><span>${esc(item.reference_date||"")}</span></div>
          <a target="_blank" rel="noopener" href="${esc(item.source.url)}">Abrir fonte</a>
        </div>
      `:"").join("")}
    </div>
  `;

  $("profileMount").className="";
  $("profileMount").innerHTML=`
    <a class="back-link" href="candidatos.html?cargo=${kind}">Voltar aos candidatos</a>

    <section class="profile-header">
      <div class="profile-copy">
        <p class="eyebrow">${kind==="federal"?"DEPUTADO FEDERAL":"DEPUTADO ESTADUAL"} · ESPÍRITO SANTO</p>
        <h1>${esc(name)}</h1>
        <p class="full-name">${esc(candidate.full_name||"")}</p>

        <div class="profile-summary">
          <div><span>Número</span><strong>${esc(candidate.number||"—")}</strong></div>
          <div><span>Partido</span><strong>${esc(candidate.party||"Não disponível")}</strong></div>
          <div><span>Situação</span><strong>${esc(candidate.registration_status||"Ainda não integrada")}</strong></div>
        </div>

        <button id="profileCompare" class="profile-compare" type="button" data-candidate-id="${esc(candidate.tse_id)}">${getCompareIds().includes(String(candidate.tse_id))?"Remover da comparação":"Adicionar à comparação"}</button>
      </div>
      ${photoMarkup(candidate,true)}
    </section>

    <nav class="profile-jump" aria-label="Conteúdo desta ficha">
      <a href="#visao-geral">Visão geral</a>
      <a href="#trajetoria">Trajetória</a>
      <a href="#temas">Temas e propostas</a>
      <a href="#registros">Registros públicos</a>
      <a href="#fontes">Fontes e limitações</a>
    </nav>

    <section class="profile-stack">
      ${profileSection("visao-geral","Visão geral","Dados da candidatura e registros institucionais já integrados",generalContent,true)}
      ${profileSection("trajetoria","Trajetória","Histórico eleitoral e atuação institucional disponível",historyContent)}
      ${profileSection("temas","Temas e propostas","Evidências temáticas documentadas quando disponíveis",topicsContent)}
      ${profileSection("registros","Registros públicos","Somente registros documentados e juridicamente qualificados",'<div class="evidence-empty">Ainda não integrada nesta versão. A ausência desta camada não implica ausência de registros.</div>')}
      ${profileSection("fontes","Fontes e limitações","Origem dos dados exibidos e limites de cobertura desta ficha",sourcesContent)}
    </section>
  `;

  $("profileCompare")?.addEventListener("click",event=>{
    const ids=toggleCompare(event.currentTarget.dataset.candidateId);
    event.currentTarget.textContent=ids.includes(String(candidate.tse_id))?"Remover da comparação":"Adicionar à comparação";
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
        <h2>Nenhum candidato selecionado.</h2>
        <p>Abra a lista e use “Comparar” em até três candidaturas.</p>
        <a href="candidatos.html?cargo=federal">Escolher candidatos</a>
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
        ${row("Ocupação declarada",candidate=>`<div class="compare-value">${esc(candidate.occupation||"Não disponível")}</div>`)}
                ${row("Escolaridade",candidate=>`<div class="compare-value">${esc(candidate.education||"Não disponível")}</div>`)}
        ${row("Registro institucional",candidate=>`<div class="compare-value">${hasInstitutional(candidate)?"Há registro integrado":"Ainda não integrado como vínculo atual"}</div>`)}
        ${row("Evidências temáticas",candidate=>`<div class="compare-value">${topicEvidence(candidate).length?`${topicEvidence(candidate).length} registro(s) documentado(s)`:"Ainda não integrada"}</div>`)}
      </div>
    </div>
    <p class="comparison-note">A comparação mostra campos disponíveis no snapshot de ${esc(formatSnapshot(meta?.collected_at))}. “Ainda não integrada” não significa ausência de proposta, posição ou experiência.</p>
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
