# Evidências temáticas por candidatura

Este arquivo define a camada que responde, com fonte, **“o que essa pessoa diz que vai fazer?”**.

Fonte canônica: `data/reference/topic-evidence.json`.

## Por que não fica em `data/generated`

`data/generated` é reconstruído pelo sync eleitoral. Propostas e declarações curadas precisam sobreviver a esse processo; por isso a fonte canônica é separada e o sync apenas anexa os registros ao candidato correspondente por `SQ_CANDIDATO`.

## Evidência mínima

Cada entrada exige:

- `candidate_id`: `SQ_CANDIDATO`;
- `topic_id`: id existente em `policy-topics.json`;
- `evidence_type`: `proposta`, `declaração` ou `atuação`;
- `statement` e/ou `quote_or_summary`;
- `source_url` HTTPS;
- `source_title`;
- `source_publisher`;
- `published_at` quando a fonte tiver data;
- `captured_at`;
- `scope`;
- `verification_status`: `verified`, `dated` ou `secondary_source`.

## Hierarquia de fonte

1. documento/portal oficial da candidatura ou partido;
2. rede social declarada ao TSE, quando a publicação for diretamente atribuível à candidatura;
3. Câmara, ALES ou outra fonte institucional para atuação;
4. fonte jornalística secundária claramente marcada.

O conjunto Candidatos 2026 do TSE publica um recurso próprio de redes sociais de candidatos. O recurso “Proposta de governo” não deve ser presumido como proposta legislativa de deputado.

## Neutralidade

A camada registra o que foi dito, proposto ou feito e a fonte correspondente.

Ela não produz:

- score;
- ranking;
- recomendação;
- afinidade;
- “beneficia você” / “prejudica você”;
- inferência de posição por partido, profissão, religião ou associação.

A camada de impacto prático pode listar **áreas potencialmente afetadas** pela evidência documentada. A conclusão valorativa permanece com a pessoa usuária.
