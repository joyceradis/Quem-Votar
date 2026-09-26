# Governador + Senado — pesquisa consolidada ES 2026

Status: research snapshot / apoio à #161  
Uso: referência para arquitetura, design, ingestão e validação.  
Regra: todos os dados devem ser revalidados no TSE e na fonte primária antes de persistência canônica.

## Como ler este documento

Este arquivo consolida o que já foi levantado sobre as 5 candidaturas ao Governo do ES e as 11 candidaturas ao Senado em 2026.

Ele NÃO é:
- ranking;
- recomendação;
- score;
- classificação ideológica própria do Quem Votar?;
- substituto da fonte oficial.

Cada candidatura deve ser normalizada no mesmo envelope descrito em:
`docs/research/CANDIDATE_RESEARCH_ARCHITECTURE_2026.md`.

---

# 1. Governador — 5 candidaturas

## Lorenzo Pazolini — REPUBLICANOS — nº 10

**SQ_CANDIDATO:** `80002552682`

### Identidade / trajetória
- Nome civil: Lorenzo Silva de Pazolini.
- Naturalidade localizada: Vitória.
- Ocupação eleitoral: servidor público estadual.
- Escolaridade: superior completo.
- Histórico público localizado: deputado estadual; prefeito de Vitória; deixou a Prefeitura em 2026 para disputar o Governo.

### Chapa
- Vice: Eliane Leal (PL).

### Patrimônio declarado
- Valor levantado: R$ 1.002.342,77.
- Revalidar no TSE antes de persistir.

### Campanha 2026
Evidências já localizadas incluem:
- conclusão dos hospitais de Cariacica e São Mateus;
- restaurantes populares;
- videomonitoramento com IA;
- proteção às mulheres;
- infraestrutura;
- expansão de programas sociais.

### Promessa × resultado
Há checagem externa publicada em 2024 sobre compromissos da campanha municipal de 2020:
- 15 compromissos avaliados;
- 7 classificados como cumpridos;
- 6 como parciais;
- 2 como não realizados naquele recorte.

**Uso no produto:** item a item, sempre atribuindo a classificação ao veículo. Não converter em nota própria.

### Fontes-base
- TSE — Candidatos 2026
- Prefeitura de Vitória
- plano oficial de governo
- A Gazeta — checagem de promessas 2020/gestão

---

## Helder Salomão — PT — nº 13

**SQ_CANDIDATO:** `80002551833`

### Identidade / trajetória
- Nome civil: Helder Ignacio Salomao.
- Naturalidade localizada: Colatina.
- Professor.
- Histórico institucional: vereador de Cariacica; deputado estadual; prefeito de Cariacica; secretário estadual; deputado federal.

### Chapa
- Vice: Professora Valdirene (PT).

### Patrimônio declarado
- Valor levantado: R$ 1.206.682,23.
- Revalidar no TSE.

### Campanha 2026
Itens localizados no plano/campanha:
- estudo de viabilidade para Tarifa Zero no Transcol;
- ampliação de consultas e exames especializados;
- segurança;
- agricultura;
- educação;
- proteção social;
- portos/logística.

### Atuação legislativa
A Câmara dos Deputados expõe, no recorte 2026, produção parlamentar suficiente para pesquisa:
- proposições de autoria;
- relatorias;
- votações nominais;
- discursos.

**Regra:** extrair matérias representativas com ID, papel e situação; não usar volume como mérito.

### Fontes-base
- TSE — Candidatos 2026
- Câmara dos Deputados — perfil e biografia
- plano oficial / canais oficiais da candidatura

---

## Breno Barcelos — MISSÃO — nº 14

**SQ_CANDIDATO:** `80002541012`

### Identidade / trajetória
- Nome civil: Breno Augusto Fagundes Barcelos.
- Naturalidade localizada: Vitória.
- Engenheiro.
- Superior completo.
- Primeira candidatura eleitoral localizada no levantamento.

### Chapa
- Vice: Victor Oliveira (MISSÃO).

### Patrimônio declarado
- Valor levantado em fonte secundária baseada no TSE: aproximadamente R$ 252.501,00.
- Houve atualização durante a campanha; revalidar diretamente no TSE.

### Campanha 2026
Propostas/declarações localizadas:
- reocupação policial de territórios controlados por facções;
- proposta de desfavelização/realocação;
- VLT/metrô Serra–Vila Velha;
- escolas cívico-militares;
- conexão entre formação técnica e setor produtivo.

### Atuação anterior
Nenhum mandato eletivo anterior localizado no sweep inicial.

### Fontes-base
- TSE — Candidatos 2026
- plano oficial de governo
- canais oficiais / entrevistas atribuíveis

---

## Ricardo Ferraço — MDB — nº 15

**SQ_CANDIDATO:** `80002552172`

### Identidade / trajetória
- Nome civil: Ricardo de Rezende Ferraço.
- Naturalidade localizada: Cachoeiro de Itapemirim.
- Atual governador do ES no recorte pesquisado.
- Histórico: vereador; deputado estadual; presidente da ALES; deputado federal; senador; vice-governador; secretário estadual; governador.

### Chapa
- Vice: Camillo Neves (PP).

### Patrimônio declarado
- Valor levantado: R$ 27.668.789,55.
- Revalidar no TSE.

### Campanha 2026
Propostas localizadas:
- conclusão de hospitais e ampliação de leitos;
- tecnologia e centro de combate a facções;
- adaptação à reforma tributária;
- escolas em tempo integral;
- infraestrutura/logística;
- saneamento;
- monitoramento climático;
- inovação e conectividade estatal.

### Atuação anterior
Pesquisar separadamente:
- Senado;
- Câmara;
- ALES;
- Governo do ES.

Não atribuir ao indivíduo toda execução coletiva do governo sem suporte documental.

### Fontes-base
- TSE — Candidatos 2026
- Governo do ES
- Senado Federal
- Câmara dos Deputados
- ALES
- plano oficial de governo

---

## Rafael Demuner — UP — nº 80

**SQ_CANDIDATO:** `80002550832`

### Identidade / trajetória
- Nome civil: Rafael Ketley Demuner.
- Naturalidade localizada: João Neiva.
- Servidor público federal.
- Superior completo.
- Primeira candidatura eleitoral registrada no levantamento.

### Chapa
- Vice: Dionary Sarmento (UP).

### Patrimônio declarado
- Valor levantado: R$ 50.550,00.
- Revalidar no TSE.

### Campanha 2026
Propostas localizadas:
- redução de jornada para servidores/terceirizados;
- tarifa zero;
- auxílio-aluguel estadual;
- taxação de imóveis abandonados;
- proposta de salário mínimo estadual de R$ 3,2 mil.

### Atuação anterior
Sem mandato eletivo anterior localizado.

### Fontes-base
- TSE — Candidatos 2026
- plano oficial de governo
- canais oficiais / entrevistas atribuíveis

---

# 2. Senado — 11 candidaturas

## Evair de Melo — REPUBLICANOS — nº 100

**SQ_CANDIDATO:** `80002553265`

### Identidade / trajetória
- Evair Vieira de Melo.
- Administrador / técnico agrícola.
- Secretário municipal de Agricultura e Meio Ambiente em Venda Nova.
- Presidente do Incaper.
- Deputado federal desde 2015.

### Patrimônio declarado
- Valor levantado: R$ 142.777,32.

### Campanha 2026
Declarações/propostas localizadas:
- emendas Pix;
- Previdência;
- escala 6x1;
- igualdade salarial;
- segurança/STF.

### Atuação legislativa
A Câmara oferece:
- proposições;
- relatorias;
- votações nominais;
- discursos.

Materializar matérias concretas e papel exato.

### Fontes-base
- TSE
- Câmara dos Deputados
- canais oficiais / entrevistas

---

## Fabiano Contarato — PT — nº 133

**SQ_CANDIDATO:** `80002550187`

### Identidade / trajetória
- Delegado da Polícia Civil e professor.
- Ex-diretor-geral do Detran.
- Ex-corregedor-geral.
- Senador desde 2019.

### Patrimônio declarado
- Valor levantado: R$ 1.497.217,78.

### Campanha 2026
Propostas/declarações localizadas:
- mandato de 10 anos para ministros do STF;
- aumento do tempo de internação para adolescentes em conflito com a lei;
- segurança pública.

### Atuação legislativa
O Senado oferece:
- proposições;
- pronunciamentos;
- relatorias;
- votações.

Exemplos já localizados para confirmação individual:
- PL 3066/2025;
- PL 4146/2020.

Registrar o papel exato em cada matéria.

### Fontes-base
- TSE
- Senado Federal

---

## Rose de Freitas — MDB — nº 156

**SQ_CANDIDATO:** `80002551368`

### Identidade / trajetória
- Rosilda de Freitas.
- Professora, jornalista/radialista.
- Deputada estadual.
- Deputada federal constituinte e em múltiplos mandatos.
- Senadora de 2015 a 2023.

### Patrimônio declarado
- Valor levantado: R$ 1.110.945,72.

### Campanha 2026
Declarações/propostas localizadas:
- reforma do Judiciário;
- posição sobre processos de cassação de ministros mediante apuração;
- duplicação da BR-262 apresentada como prioridade orçamentária.

### Atuação legislativa
Fontes institucionais fortes:
- Câmara;
- Senado;
- Arquivo do Senado.

O Arquivo do Senado registra atuação na Constituinte e emendas apresentadas; materializar itens verificáveis individualmente.

### Fontes-base
- TSE
- Câmara dos Deputados
- Senado Federal / Arquivo do Senado

---

## Maguinha Malta — PL — nº 222

**SQ_CANDIDATO:** `80002553269`

### Identidade / trajetória
- Magda Santos Malta.
- Publicitária, música/produtora musical.
- Sem cargo eletivo anterior localizado no sweep inicial.

### Patrimônio declarado
- Valor levantado: R$ 116.534,48.

### Campanha 2026
Declarações/propostas localizadas:
- penas mais duras e fim de indulto para criminosos;
- redução da maioridade penal para 14 anos;
- vacinação sem obrigatoriedade;
- educação;
- bets;
- impostos.

### Atuação anterior
Não inferir trajetória própria a partir de vínculo familiar ou partidário.

### Fontes-base
- TSE
- canais oficiais / entrevistas

---

## Wellington Callegari — DC — nº 277

**SQ_CANDIDATO:** `80002542401`

### Identidade / trajetória
- Professor.
- Servidor público.
- Produtor de conteúdo digital.
- Deputado estadual desde 2023.

### Patrimônio declarado
- Valor levantado: R$ 850.000,00.

### Campanha 2026
Declarações/propostas localizadas:
- posições sobre aborto;
- críticas à reforma tributária;
- defesa de mudanças no Código Penal.

### Atuação legislativa
Extrair da ALES:
- proposições;
- votações;
- comissões;
- requerimentos;
- discursos.

### Fontes-base
- TSE
- ALES

---

## Rodney Miranda — PRTB — nº 280

**SQ_CANDIDATO:** `80002552373`

### Identidade / trajetória
- Rodney Rocha Miranda.
- Delegado da Polícia Civil/DF.
- Professor e consultor.
- Secretário de Segurança em governos estaduais.
- Deputado estadual.
- Prefeito de Vila Velha.
- Secretário estadual em outras áreas.

### Patrimônio declarado
- Valor levantado: R$ 4.594.177,63.

### Campanha 2026
Declarações/propostas localizadas:
- novo modelo de distribuição de recursos com maior parcela aos municípios;
- segurança pública;
- STF.

### Atuação anterior
Mapear:
- Prefeitura de Vila Velha;
- governos ES/GO;
- ALES;
- atos e resultados institucionais.

### Fontes-base
- TSE
- Prefeitura de Vila Velha
- governos estaduais correspondentes
- ALES

---

## Leonardo Monjardim — NOVO — nº 300

**SQ_CANDIDATO:** `80002530022`

### Identidade / trajetória
- Leonardo Passos Monjardim.
- Empresário, professor e escritor.
- Atuação anterior como vereador de Vitória registrada no levantamento.

### Patrimônio declarado
- Valor levantado: R$ 222.000,00.

### Campanha 2026
Declarações/propostas localizadas:
- redução de tributos;
- flexibilização de normas ambientais em projetos estruturantes;
- empreendedorismo;
- câmeras em escolas;
- rejeição a câmeras corporais em policiais;
- fim de radares;
- fim de emendas parlamentares em entrevista.

### Atuação anterior
Confirmar diretamente na Câmara Municipal de Vitória:
- período;
- proposições;
- votações;
- comissões.

### Fontes-base
- TSE
- Câmara Municipal de Vitória

---

## Renato Casagrande — PSB — nº 400

**SQ_CANDIDATO:** `80002551370`

### Identidade / trajetória
- José Renato Casagrande.
- Engenheiro florestal e advogado.
- Deputado estadual.
- Vice-governador.
- Deputado federal.
- Senador.
- Governador do ES em diferentes períodos.

### Patrimônio declarado
- Valor levantado: R$ 3.068.203,91.

### Campanha 2026
Três bandeiras explicitamente localizadas:
- maior protagonismo do Espírito Santo;
- transparência nas emendas parlamentares;
- reforma do Judiciário.

Essas podem ser tratadas como prioridade/bandeira documentada, desde que a fonte correspondente esteja vinculada.

### Promessa × resultado
Há avaliação externa publicada sobre o ciclo 2019–2022:
- 42 compromissos avaliados;
- 26 classificados como cumpridos;
- 10 parciais;
- 6 não cumpridos.

Exemplo de pendências naquele recorte:
- mobilidade, incluindo aquaviário/BRT.

Separar claramente:
- mandato 2019–2022;
- ciclo 2023–2026;
- período posterior já sob outro titular.

### Fontes-base
- TSE
- Governo do ES
- Senado
- Câmara
- A Gazeta — checagem de promessas

---

## Professor Fabian — PSOL — nº 500

**SQ_CANDIDATO:** `80002549404`

### Identidade / trajetória
- Carlos Fabian de Carvalho.
- Professor.
- Sem cargo eletivo anterior localizado no sweep inicial.

### Patrimônio declarado
- Valor levantado: R$ 264.795,32.

### Campanha 2026
Declarações/propostas localizadas:
- revisão das reformas trabalhista e previdenciária;
- fim da escala 6x1;
- PEC da Cultura;
- câmeras em escolas/fardas;
- combate ao financiamento do tráfico.

### Atuação anterior
Sem atuação eletiva anterior localizada.

### Fontes-base
- TSE
- canais oficiais / entrevistas atribuíveis

---

## Sergio Meneguelli — PSD — nº 556

**SQ_CANDIDATO:** `80002552692`

### Identidade / trajetória
- Produtor cultural.
- Vereador de Colatina em diferentes períodos.
- Prefeito de Colatina (2017–2020).
- Deputado estadual desde 2023.

### Patrimônio declarado
- Valor levantado: R$ 1.188.865,04.

### Campanha 2026
No sweep inicial, não foi encontrada evidência robusta o suficiente para rotular uma pauta como prioridade de campanha.

### Atuação anterior
Extrair:
- ALES — proposições, votos, requerimentos e comissões;
- Prefeitura/Diário — entregas verificáveis do período como prefeito;
- checagens externas metodologicamente explícitas, se existirem.

### Fontes-base
- TSE
- ALES
- Prefeitura de Colatina

---

## Marcos do Val — AVANTE — nº 700

**SQ_CANDIDATO:** `80002538202`

### Identidade / trajetória
- Marcos Ribeiro do Val.
- Militar e empresário.
- Senador desde 2019.

### Patrimônio declarado
- Valor levantado: R$ 584.138,00.

### Campanha 2026
Declarações/propostas localizadas:
- posição contrária ao fim da escala 6x1;
- flexibilização do porte de armas;
- integração/unificação de sistemas de segurança;
- proibição de bets/jogos;
- posições sobre STF.

### Atuação legislativa
O Senado disponibiliza:
- proposições;
- relatorias;
- pronunciamentos;
- votações;
- composição de comissões.

Exemplos já localizados para confirmação individual:
- PL 1796/2025;
- PEC 32/2024;
- PL 2573/2021.

Confirmar autoria, papel e tramitação antes de persistir.

### Fontes-base
- TSE
- Senado Federal

---

# 3. Campos que ainda precisam ser materializados

Antes de chamar este dossiê de completo, falta:

## Para todos os 16
- revalidar situação eleitoral no TSE;
- revalidar patrimônio;
- vice/suplentes;
- redes oficiais;
- foto TSE;
- histórico eleitoral completo;
- fonte individual por afirmação;
- data de captura.

## Para Governador
- extrair os 5 PDFs oficiais de plano de governo;
- quebrar cada plano em propostas estruturadas;
- identificar apenas prioridades explicitamente sustentadas;
- mapear entregas anteriores de quem já exerceu Executivo.

## Para Senado
- materializar atos legislativos individuais;
- extrair ALES/Câmara/Senado/Câmaras municipais conforme trajetória;
- materializar entrevistas e declarações 2026 com link individual;
- separar proposta atual de atuação passada.

## Justiça / registros eleitorais
- coletar certidões e registros oficiais quando disponíveis;
- não usar busca nominal solta como fonte canônica;
- contextualizar status e resultado.

## Orientação partidária
- adotar metodologia externa identificada;
- atribuir classificação à fonte;
- não inferir ideologia individual apenas pela sigla.

---

# 4. Regra editorial

Sempre distinguir:
- proposta;
- declaração;
- prioridade documentada;
- atuação;
- promessa anterior;
- resultado observado;
- avaliação externa.

E sempre preservar:
- fonte;
- data;
- papel da pessoa;
- status;
- lacunas.
