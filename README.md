# Quem Votar? — Espírito Santo 2026

Plataforma cívica open source para consulta factual e rastreável de candidaturas a Deputado Federal e Deputado Estadual no Espírito Santo.

**Licença do software original:** GNU AGPL v3.0 only (`AGPL-3.0-only`). Dados e materiais provenientes de fontes externas permanecem sujeitos aos termos de suas fontes.

**Produção:** https://joyceradis.github.io/Quem-Votar/

**Baseline visual atual:** `V5.5` · versão canônica em [`VERSION`](VERSION)

## Onde acompanhar o projeto

Cada documento tem uma função diferente:

- **README:** explica o produto e o estado estável atual.
- **Roadmap:** mostra a direção macro e a ordem das próximas frentes.
- **Issues:** concentram tarefas concretas, bugs, decisões e critérios de pronto.
- **Checkpoint:** registra o estado técnico datado da branch canônica.

O trabalho executável deve ser acompanhado nas [Issues do repositório](https://github.com/joyceradis/Quem-Votar/issues). O README não replica uma lista de Issues ativas porque esse estado muda com frequência.

## Recorte atual

A versão pública cobre:

- Deputado Federal;
- Deputado Estadual;
- Espírito Santo;
- Eleições Gerais de 2026.

Outros cargos ainda não aparecem na interface pública.

## Snapshot eleitoral

A interface não publica contagens como números permanentes no código. Ela lê a data e os totais do snapshot em:

`data/generated/meta.json`

O site mostra:

- data e hora do snapshot;
- total federal;
- total estadual;
- link para a fonte primária do TSE.

A data é exibida no fuso `America/Sao_Paulo`.

## Experiência pública V5.5

### Home

- cargo e busca aparecem no primeiro fluxo;
- identidade visual capixaba em azul, branco e rosa;
- elemento vetorial regional leve no hero;
- contagens e snapshot ligados à fonte TSE;
- três caminhos principais: nome, assunto ou comparação;
- assuntos só aparecem quando existe evidência temática documentada.

### Candidaturas

- 12 resultados por página;
- busca dominante;
- filtros secundários sob demanda;
- filtro por partido;
- filtro por tema documentado;
- registro institucional integrado quando disponível;
- seleção de até 3 candidaturas para comparação;
- cartões com hierarquia editorial e tags temáticas somente quando existe `topic_evidence`.

As tags não são inferidas a partir de partido, profissão, ocupação, religião ou associação.

### Temas

`Saúde`, `Educação`, `Segurança`, `Economia` e os demais temas representam **propostas, declarações ou atuação documentada** da candidatura.

A taxonomia pública fica em:

`data/reference/policy-topics.json`

Profissão/ocupação declarada ao TSE é apenas metadado da ficha e não associa uma candidatura a um tema.

### Ficha individual

Leitura em camadas:

- Visão geral;
- Trajetória;
- Temas e propostas;
- Registros públicos;
- Fontes e limitações;
- compartilhamento direto da ficha por URL.

### Comparação

Até 3 candidaturas lado a lado, com os mesmos campos factuais/documentais.

Não existe score, ranking, vencedor, previsão eleitoral ou recomendação de voto.

## Evidências temáticas

Fonte canônica:

`data/reference/topic-evidence.json`

Fluxo de integração:

`fonte permitida → staging → validação → revisão semântica → promoção explícita → sync → interface`

A infraestrutura de coleta fica em `scripts/coletor_evidencias.py`.

Regras centrais:

- `SQ_CANDIDATO` é a chave eleitoral canônica;
- perfis sociais declarados ao TSE são sementes de descoberta, não evidências por si só;
- conteúdo coletado entra primeiro em `data/staging/`;
- PDF textual pode ser extraído sem OCR automático;
- `topic_id` e `evidence_type` não são inferidos durante a coleta;
- promoção para a fonte canônica exige validação explícita;
- ausência de evidência continua sendo ausência de dado.

## Fontes e proveniência

### TSE

Fonte eleitoral primária e origem das fotografias eleitorais utilizadas na plataforma.

### Câmara dos Deputados

Dados institucionais federais vinculados de forma conservadora.

### ALES

Evidências documentais estaduais datadas. Evidência histórica não é promovida automaticamente a situação atual.

Quando uma imagem ou dado usa transporte intermediário por limitação operacional, origem e transporte devem permanecer registrados separadamente.

## Regra de integridade

**Uma lacuna permanece lacuna até existir fonte identificável, vínculo justificável e tratamento documentado.**

## Manutenção deste README

O README deve representar **estado estável**, não o backlog em tempo real.

Atualize este arquivo quando ocorrer pelo menos uma destas mudanças:

1. mudança de versão/baseline público;
2. alteração do recorte eleitoral suportado;
3. nova funcionalidade pública consolidada;
4. mudança de fonte canônica ou fluxo de dados relevante;
5. fechamento de uma frente que torne alguma descrição deste arquivo incorreta.

Não é necessário atualizar o README a cada commit, PR ou comentário de Issue.

Distribuição de responsabilidade documental:

- **README:** estado estável e visão do produto;
- **`VERSION`:** versão canônica;
- **`docs/CHECKPOINT_CURRENT.md`:** estado técnico datado;
- **`docs/ROADMAP_V1.md`:** prioridades macro;
- **Issues:** execução diária e decisões específicas.

Antes de fechar uma Issue que altere versão, escopo, experiência pública ou arquitetura de dados, verificar se README e checkpoint ainda descrevem corretamente a `main`.

## Governança

Leia antes de alterar:

- `AGENTS.md`
- `docs/GOVERNANCE.md`
- `docs/DELIVERY_GOVERNANCE.md`
- `docs/PRODUCT_NORTH_STAR.md`
- `docs/TOPIC_EVIDENCE.md`
- `docs/CHECKPOINT_CURRENT.md`
- `docs/FILTERS.md`
- `docs/DATA_MODEL.md`
- `docs/SITE_MAP.md`
- `METODOLOGIA.md`
- `AUDITORIA.md`


## Licenciamento

O software original deste repositório é distribuído sob a **GNU Affero General Public License v3.0 only (AGPL-3.0-only)**. Consulte [LICENSE](LICENSE).

A licença do software não transforma automaticamente dados, documentos, fotografias ou outros materiais de terceiros em conteúdo AGPL. Esses materiais permanecem sujeitos aos direitos, termos e condições das respectivas fontes.

A identidade visual e o nome do projeto não devem ser interpretados como autorização para sugerir endosso institucional, político ou comercial por parte do projeto ou de sua mantenedora.


### Software Licensing and Trademark Use

The AGPL-3.0-only license applies to the original software identified in this repository. It does not grant authorization to use the “Quem Votar?” name, logos, trademarks or other distinctive signs, nor to imply endorsement, association or partnership with the project or its maintainer.

Third-party data, documents, photographs and other materials remain subject to the licenses, rights and terms of their respective sources.

Detailed rules for visual assets and trademark usage may be documented separately in a future `TRADEMARK_POLICY.md`.
