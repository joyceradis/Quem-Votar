# Checkpoint atual — V5

Data: 2026-09-19.

## Estado canônico

Branch: `main`.

Baseline visual: `V5.3`. Cache de assets: `5.3.0`.

Este checkpoint não cria sozinho um GitHub Release formal.

## Contrato público

- Deputado Federal e Deputado Estadual no Espírito Santo;
- busca e cargo no primeiro fluxo;
- 12 resultados por página;
- comparação de até 3 candidaturas;
- ficha vertical por camadas;
- sem score, ranking, vencedor ou recomendação.

## Correção semântica V5

`Saúde`, `Educação`, `Segurança`, `Economia` e demais temas representam propostas, declarações ou atuação documentada.

Ocupação declarada ao TSE é apenas metadado. Não gera tema, posição política ou avaliação.

Taxonomia temática pública: `data/reference/policy-topics.json`.

## Interface

- home orientada às perguntas “o que faz hoje?”, “o que diz que vai fazer?” e “onde isso mexe na vida real?”;
- menu principal lateral em todas as larguras;
- linguagem pública sem jargão de auditoria no primeiro nível;
- assuntos explicam áreas da vida potencialmente afetadas sem classificar benefício ou prejuízo;
- stylesheet canônico sem camadas de override herdadas;
- cargo e busca dominam o primeiro viewport;
- filtros secundários aparecem sob demanda;
- listagem é editorial e compacta;
- nome/cargo/partido/número têm precedência sobre foto e ocupação;
- ficha: Visão geral -> Trajetória -> Temas e propostas -> Registros públicos -> Fontes e limitações;
- favicon SVG e manifesto web configurados;
- identidade visual em azul, branco e rosa; azul conduz interação e rosa funciona apenas como acento de marca;
- mudança visual deve ser entregue em commit atômico conforme `docs/DELIVERY_GOVERNANCE.md`.

## Dados preservados

- `SQ_CANDIDATO` continua chave canônica;
- snapshots TSE não foram reinterpretados;
- Câmara e ALES preservam critérios de vínculo;
- lacuna continua sendo lacuna.

## Pendências de conteúdo

- histórico eleitoral TSE completo;
- bens;
- redes sociais;
- cobertura contemporânea completa da ALES;
- propostas/posições temáticas em escala;
- atividade parlamentar temática;
- registros públicos juridicamente qualificados.

## Gates

Antes de considerar a V5 estável:
1. `node --check app.js` verde;
2. `scripts/audit-site.py` verde;
3. workflow Quality verde;
4. GitHub Pages verde;
5. navegação Home -> Candidatos -> Ficha -> Comparar verificada.

## Camada de propostas e declarações

Fonte canônica: `data/reference/topic-evidence.json`.

O sync eleitoral anexa essa camada por `SQ_CANDIDATO` sem apagá-la. No checkpoint atual, a cobertura é **0 registros**, portanto a interface deve declarar a lacuna em vez de inferir posição.

A expansão dessa camada é acompanhada pela issue #2.
