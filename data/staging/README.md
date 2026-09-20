# Staging de evidências temáticas

Esta pasta é intermediária. Nada aqui é exibido diretamente na interface pública.

Fluxo:

`fonte permitida → sources → drafts → reviews → promote → data/reference/topic-evidence.json`

## Arquivos

- `topic-evidence-sources.json`: fila de fontes e sementes de descoberta.
- `topic-evidence-drafts.json`: conteúdo bruto coletado, com hash e trecho auditável.
- `topic-evidence-reviews.json`: decisão semântica separada da coleta.
- `topic-evidence-rejections.json`: criado pelo coletor quando uma URL falha ou é rejeitada.

Perfis de redes sociais declarados ao TSE entram como `discovery_status: "seed"`. Um perfil não é uma evidência. Para coleta, é necessário um link de conteúdo específico (`exact_content`), como matéria, post, vídeo ou documento identificável.

## Dependência para PDFs

A coleta de PDF textual usa `pypdf 6.19.0`, fixado em `requirements-evidence.txt`.

Instalação:

```bash
python -m pip install -r requirements-evidence.txt
```

Projeto: https://pypi.org/project/pypdf/  
Licença: BSD-3-Clause.

O coletor **não executa OCR automaticamente**. PDF sem camada textual suficiente é rejeitado e permanece fora da fonte canônica.

## Comandos

Descobrir redes declaradas ao TSE para as candidaturas presentes no snapshot:

```bash
python scripts/coletor_evidencias.py discover-tse-socials
```

Adicionar manualmente uma URL específica descoberta por pesquisa:

```bash
python scripts/coletor_evidencias.py add-source \
  --candidate-id SQ_CANDIDATO_REAL \
  --url https://exemplo.org/noticia/conteudo-especifico \
  --source-kind official_candidate \
  --publisher "Portal oficial"
```

Coletar as URLs específicas:

```bash
python scripts/coletor_evidencias.py collect
```

Validar staging e reviews:

```bash
python scripts/coletor_evidencias.py validate
```

Testar uma promoção sem alterar a fonte canônica:

```bash
python scripts/coletor_evidencias.py promote
```

Somente depois de revisão aprovada e em branch/PR apropriado:

```bash
python scripts/coletor_evidencias.py promote --write-canonical
```

## Revisão semântica

Uma revisão aprovada precisa registrar, no máximo após 3 tentativas:

- `draft_id`;
- `status: "approved"`;
- `attempts`;
- `topic_id`;
- `evidence_type`: `proposta`, `declaração` ou `atuação`;
- `statement` e/ou `quote_or_summary`;
- `scope`;
- `verification_status`;
- `support_text`: trecho que precisa existir no material bruto coletado;
- `attribution_basis`: por que a evidência é atribuível à candidatura;
- `reviewed_at`;
- `reviewer`.

Se houver ambiguidade relevante, usar `quarantine` ou `rejected`. Ausência de evidência não é convertida em posição política.

## Metadado futuro fora da pipeline de evidências

`candidate-political-spectrum.json` preserva, em staging, a coluna `ESPECTRO_POLÍTICO` fornecida pela mantenedora na matriz de curadoria.

Esse arquivo:

- não é `topic_evidence`;
- não é produzido por inferência de partido, ocupação, religião, associação ou evidência temática;
- não é consumido pela interface pública durante o Feature Freeze;
- não altera ordenação, visibilidade, comparação ou recomendação de candidaturas;
- registra os valores fornecidos pela mantenedora sem tratá-los como classificação independente do pipeline;
- só pode ganhar uso público após decisão metodológica e de governança pós-freeze.

