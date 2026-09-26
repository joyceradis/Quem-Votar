# Quem Votar? — Espírito Santo 2026

Plataforma cívica open source para consulta factual e rastreável de candidaturas a Deputado Federal e Deputado Estadual no Espírito Santo.

**Licença do software original:** GNU AGPL v3.0 only (`AGPL-3.0-only`). Dados e materiais provenientes de fontes externas permanecem sujeitos aos termos de suas fontes.

**Produção:** https://joyceradis.github.io/Quem-Votar/

**Baseline visual:** produção **V5.5** no ar · **V6.0.0 preparada para cutover**
(reconstrução em `src/`, corte date-gated a partir de 04/10/2026). O arquivo
[`VERSION`](VERSION) já registra `6.0.0`, a versão **preparada** — não a
publicada: as páginas no ar ainda servem os assets `V5.5`. Ver
[`docs/REBUILD_V6.md`](docs/REBUILD_V6.md).

[Produção](https://joyceradis.github.io/Quem-Votar/) · [Como funciona](sobre.html) · [Metodologia](METODOLOGIA.md) · [Apoiar o projeto](apoio.html) · [GitHub Sponsors](https://github.com/sponsors/joyceradis) · [Licença](LICENSE)

## Onde acompanhar o projeto

Cada documento tem uma função diferente:

- **README:** explica o produto e o estado estável atual.
- **Roadmap:** mostra a direção macro e a ordem das próximas frentes.
- **Issues:** concentram tarefas concretas, bugs, decisões e critérios de pronto.
- **Checkpoint:** registra o estado técnico datado da branch canônica.

O trabalho executável deve ser acompanhado nas [Issues do repositório](https://github.com/joyceradis/Quem-Votar/issues). O README não replica uma lista de Issues ativas porque esse estado muda com frequência.

### Entrada canônica para agentes e contribuidores

Antes de alterar o projeto:

1. leia `AGENTS.md` e `docs/GOVERNANCE.md`;
2. pesquise a Issue/PR ativa da lane antes de criar trabalho novo;
3. consulte `docs/ROADMAP_V1.md` quando precisar entender dependências macro;
4. consulte `docs/CHECKPOINT_CURRENT.md` apenas como snapshot técnico datado, nunca como substituto do estado atual;
5. trabalhe na Issue de responsabilidade mais específica aplicável.

Uma Issue executável deve ter **uma responsabilidade principal**. Tracking Issues coordenam dependências, mas não substituem os critérios de pronto das Issues-filhas.

Não criar pipeline, script ou modelo específico por candidatura. O processamento é orientado por dados e usa `SQ_CANDIDATO` como identidade canônica.

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

O funil de comparação está consolidado com seleção de até 3 pessoas, feedback acessível, foco preservado nos fluxos cobertos, normalização de URLs inválidas/duplicadas, sincronização entre abas e validação em desktop/mobile/teclado.

Não existe score, ranking, vencedor, previsão eleitoral ou recomendação de voto.

### Compartilhamento social

Cada candidatura possui uma entrada estática em `/social/<SQ_CANDIDATO>/index.html` para metadados Open Graph. Essas páginas não duplicam a ficha: o corpo é vazio e o fluxo direciona para a URL canônica da candidatura.

### Camadas factuais integradas

Além do cadastro eleitoral básico, o snapshot público preserva, quando disponíveis e com proveniência identificada:

- bens declarados;
- redes sociais declaradas ao TSE;
- histórico eleitoral;
- vínculo institucional atual/histórico.

Ausência de uma dessas camadas continua sendo ausência de dado, não conclusão sobre a candidatura.

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
- `docs/RUNTIME_PROOF.md`
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


## Apoie o projeto

O **Quem Votar?** é gratuito para quem consulta e open source. Contribuições ajudam a custear manutenção, dados, documentação e infraestrutura sem conceder qualquer influência sobre o conteúdo eleitoral.

### GitHub Sponsors

O perfil **GitHub Sponsors** da mantenedora está ativo e público. O repositório usa `.github/FUNDING.yml` para exibir o botão nativo **Sponsor**.

[Apoiar via GitHub Sponsors](https://github.com/sponsors/joyceradis)

### PIX

Chave PIX (e-mail):

`contato@drajoyceradis.com`

Apoio financeiro não altera fontes, metodologia, temas, ordem, classificação ou apresentação de candidaturas.

Mais detalhes: [apoio e transparência](apoio.html) · [arquitetura de sustentabilidade](docs/SUSTAINABILITY.md).
