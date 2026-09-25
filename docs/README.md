# Documentação — mapa de responsabilidades

Este diretório reúne documentação especializada do **Quem Votar?**.

Este arquivo é um **índice de navegação**, não uma fonte concorrente de estado.  
Para estado executável, consulte a Issue/PR ativa e as evidências ligadas ao SHA aplicável.

## Ordem de autoridade

1. `main`;
2. `AGENTS.md`;
3. `docs/GOVERNANCE.md`;
4. contrato ativo da Issue/PR;
5. checks, artifacts e runtime ligados ao SHA aplicável;
6. `docs/CHECKPOINT_CURRENT.md` apenas como snapshot histórico datado.

## Produto

- `PRODUCT_NORTH_STAR.md` — problema que o produto resolve, perguntas públicas e linguagem.
- `SITE_MAP.md` — superfícies e rotas públicas.
- `FILTERS.md` — semântica de filtros e comparação.
- `DESIGN_REFERENCES.md` — referências de design e limites de implementação.
- `SUSTAINABILITY.md` — separação entre financiamento e camada editorial eleitoral.

## Dados e evidências

- `DATA_MODEL.md` — estruturas e contratos de dados.
- `TOPIC_EVIDENCE.md` — evidências temáticas por candidatura.
- `TELEMETRY_PRIVACY.md` — contrato de minimização e prova de privacidade da telemetria.

## Governança e entrega

- `GOVERNANCE.md` — regras de dados, produto, neutralidade e governança multiagente.
- `DELIVERY_GOVERNANCE.md` — gates de entrega, CSS, workflows e validação.
- `RUNTIME_PROOF.md` — contrato do harness canônico de prova de runtime.
- `runtime-proof-manifest.schema.json` — schema do artifact de runtime.
- `ROADMAP_V1.md` — direção macro e dependências de produto/engenharia.
- `CHECKPOINT_CURRENT.md` — snapshot técnico datado; não prevalece sobre estado atual.

## Licenciamento

- `LICENSING.md` — relação entre licença do software, dados de terceiros e identidade do projeto.
- `../LICENSE` — texto integral da AGPL-3.0-only.

## Relatórios históricos

Os arquivos abaixo registram investigação e decisões em momentos específicos. Eles não devem ser usados isoladamente como descrição do estado atual:

- `../AUDITORIA.md`;
- seções datadas de `CHECKPOINT_CURRENT.md`.

Quando uma afirmação histórica divergir da `main`, de regra normativa posterior ou de contrato ativo, preserve o histórico e use a fonte de maior autoridade para a decisão atual.

## Regra de manutenção

Não duplicar neste índice:

- status de Issue;
- estado de PR;
- SHA atual;
- resultado de CI;
- ownership temporário de agentes;
- backlog.

Essas informações mudam com frequência e pertencem ao GitHub como system of record.
