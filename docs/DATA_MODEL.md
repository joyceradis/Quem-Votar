# Modelo de dados — V1

## Candidate

```json
{
  "candidate_id": "SQ_CANDIDATO",
  "election_year": 2026,
  "uf": "ES",
  "office": "DEPUTADO FEDERAL",
  "ballot_name": "string",
  "full_name": "string",
  "number": 1234,
  "party": "SIGLA",
  "party_name": "string"
}
```

## EvidenceEnvelope

Todo bloco enriquecido deve poder responder: quem disse, onde, quando e em qual contexto.

```json
{
  "status": "verified | dated | not_integrated | not_available | secondary_source",
  "source": {
    "institution": "string",
    "title": "string",
    "url": "https://...",
    "published_at": "YYYY-MM-DD",
    "captured_at": "ISO-8601"
  }
}
```

## OfficeHistory

```json
{
  "institution": "Câmara dos Deputados",
  "office": "Deputado Federal",
  "start": "YYYY-MM-DD|null",
  "end": "YYYY-MM-DD|null",
  "legislature": "string|null",
  "condition": "string|null",
  "status": "string|null",
  "evidence": {}
}
```

## PartyHistory

```json
{
  "party": "SIGLA",
  "start": "YYYY-MM-DD|null",
  "end": "YYYY-MM-DD|null",
  "source": {}
}
```

Mudança partidária é um fato cronológico. O produto não atribui "coerência" ou "incoerência"; apenas apresenta a sequência documentada.

## TopicEvidence

Fonte canônica: `data/reference/topic-evidence.json`.

```json
{
  "candidate_id": "SQ_CANDIDATO",
  "topic_id": "seguranca",
  "evidence_type": "proposta | declaração | atuação",
  "statement": "Resumo factual curto",
  "quote_or_summary": "Trecho ou resumo fiel à fonte",
  "source_url": "https://...",
  "source_title": "string",
  "source_publisher": "string",
  "published_at": "YYYY-MM-DD|null",
  "captured_at": "ISO-8601",
  "scope": "federal | estadual | municipal | geral",
  "verification_status": "verified | dated | secondary_source"
}
```

A coleta automatizada não escreve diretamente nessa fonte. Material bruto passa por `data/staging/`, revisão semântica e validação determinística antes de qualquer promoção.

## Coverage

Cada ficha deve expor cobertura:

```json
{
  "electoral_history": "verified",
  "party_history": "not_integrated",
  "assets": "not_integrated",
  "campaign_finance": "not_integrated",
  "parliamentary_activity": "verified"
}
```

Isso impede que ausência visual pareça inexistência factual.
