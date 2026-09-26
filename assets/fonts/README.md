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
| Inter | Texto, interface e dados | Copyright 2020 The Inter Project Authors | https://github.com/rsms/inter |
| Bricolage Grotesque | Títulos (display) | Copyright 2022 The Bricolage Grotesque Project Authors | https://github.com/ateliertriay/bricolage |

## Por que estas duas

Quatro famílias foram comparadas lado a lado (Fraunces, Instrument Serif,
Bricolage Grotesque e Inter em peso alto). As duas serifadas foram descartadas
por legibilidade: têm traço fino de alto contraste, que degrada em tela pequena
e em telas de baixa qualidade — e o público real do produto acessa
majoritariamente por celular. `AGENTS.md` §6 trata legibilidade e acessibilidade
como requisito, não preferência.

`Bricolage Grotesque` mantém personalidade (o `PRODUCT_NORTH_STAR.md` pede
"produto de consumo, não portal institucional") sem pagar esse preço, e conversa
com o desenho do logo. `Inter` cobre texto corrido, interface e dados numéricos.

As famílias descartadas foram removidas deste diretório e de
`src/styles/fonts.css` — não se publica peso morto.
