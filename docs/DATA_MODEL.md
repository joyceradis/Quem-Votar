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

```json
{
  "topic_id": "seguranca-publica",
  "candidate_id": "SQ_CANDIDATO",
  "evidence_type": "official_program | candidate_statement | roll_call_vote | bill | official_interview",
  "statement": "Resumo factual curto",
  "source": {},
  "scope": "federal | estadual | municipal | geral",
  "verification_status": "verified"
}
```

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
