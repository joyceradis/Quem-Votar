# Fontes auto-hospedadas

Origem e licenciamento das famílias tipográficas usadas pela interface V6,
conforme exige `docs/DESIGN_REFERENCES.md` ("Regra de implementação": licença
explícita compatível, origem registrada, atribuição preservada).

Todas são distribuídas sob a **SIL Open Font License 1.1** (OFL-1.1),
compatível com a AGPL-3.0-only do software deste repositório. A OFL cobre
apenas os arquivos de fonte; não altera a licença do restante do projeto.

O texto integral da licença está em [`OFL.txt`](OFL.txt).

## Por que auto-hospedadas

Carregar via CDN do Google faria cada visitante emitir uma requisição a
terceiros carregando seu IP e User-Agent. Isso contraria a postura de
privacidade registrada em `docs/TELEMETRY_PRIVACY.md` e `docs/GOVERNANCE.md`.
Servindo os arquivos do próprio domínio, a página não faz nenhuma requisição
externa.

Os arquivos são os subsets `latin` e `latin-ext` em `woff2`, obtidos da API
oficial do Google Fonts. O `latin-ext` só é baixado pelo navegador quando a
página contém algum caractere daquele intervalo (`unicode-range`); em
português, o caso normal carrega apenas o `latin`.

## Famílias

| Família | Uso | Copyright | Upstream |
|---|---|---|---|
| Inter | Texto e interface | Copyright 2020 The Inter Project Authors | https://github.com/rsms/inter |
| Fraunces | Títulos (display) | Copyright 2018 The Fraunces Project Authors | https://github.com/undercasetype/Fraunces |
| Instrument Serif | Candidata a display | Copyright 2022 The Instrument Serif Project Authors | https://github.com/Instrument/instrument-serif |
| Bricolage Grotesque | Candidata a display | Copyright 2022 The Bricolage Grotesque Project Authors | https://github.com/ateliertriay/bricolage |

## Pendência antes da Fase 5

`Instrument Serif` e `Bricolage Grotesque` estão aqui apenas como **candidatas
em comparação** na página interna de styleguide. Assim que a mantenedora
escolher a família de títulos, as não escolhidas devem ser removidas deste
diretório e de `src/styles/fonts.css` — não faz sentido publicar peso morto.
