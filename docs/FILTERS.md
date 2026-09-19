# Filtros e semântica

## Objetivo

Os filtros reduzem o universo de candidaturas por dados documentados. Eles não calculam afinidade, não ordenam candidatos por valor e não recomendam voto.

## Filtros ativos

### Cargo
Fonte: cadastro eleitoral 2026.

### Partido
Fonte: cadastro eleitoral 2026.

### Tema documentado
Um tema de política pública só é associado a uma candidatura quando existe `topic_evidence` individualizada e documentada.

A taxonomia fica em `data/reference/policy-topics.json`.

Ocupação, profissão, partido, religião, associação ou cor não geram associação temática.

### Registro institucional
Mostra candidaturas com vínculo ou evidência institucional já documentada na base.

## Ausência de evidência

`Ainda não integrado` não significa `não possui proposta`, `nunca atuou` ou `é contra/favorável`. A interface não converte lacuna em conclusão.

## Comparação

A comparação usa os mesmos campos factuais e documentais disponíveis na ficha. Não produz score, ranking, vencedor ou recomendação.