# Quem Votar? — Espírito Santo 2026

**Produto cívico para consultar candidaturas com dados públicos, fontes rastreáveis e regras explícitas para lidar com incerteza.**

O projeto organiza cadastro eleitoral, histórico institucional e evidências documentadas em uma interface de busca, ficha e comparação. A proposta é facilitar a leitura de informação pública sem transformar cobertura documental em ranking, afinidade ou recomendação de voto.

[**Abrir produto**](https://joyceradis.github.io/Quem-Votar/) · [Metodologia](METODOLOGIA.md) · [Auditoria](AUDITORIA.md) · [Documentação técnica](docs/README.md) · [Licença](LICENSE)

> Versão pública atual: **V6.0.0**. O recorte visível cobre candidaturas a Governador, Senador, Deputado Federal e Deputado Estadual no Espírito Santo, sem criar fluxos específicos por candidatura.

---

## O produto

O Quem Votar? foi construído para responder perguntas práticas sem esconder a origem da informação:

- encontrar uma candidatura por nome, número ou partido;
- consultar dados eleitorais e institucionais em uma ficha única;
- navegar por assuntos somente quando existe evidência documentada;
- comparar até três candidaturas lado a lado, sem produzir vencedor;
- acessar a fonte usada para sustentar cada camada factual;
- distinguir ausência de dado de ausência de proposta, atuação ou posição.

A interface é mobile-first e mantém busca, comparação, estados vazios, navegação por teclado e compartilhamento direto por URL.

---

## O que este repositório demonstra

| Área | Implementação |
| --- | --- |
| **Data engineering** | pipeline em Python para ingestão, normalização, proveniência e geração de snapshots eleitorais |
| **Modelagem de domínio** | `SQ_CANDIDATO` como identidade canônica, contratos por cargo e separação entre cadastro, evidência e apresentação |
| **Frontend** | Eleventy no build; HTML, CSS e JavaScript puros na entrega pública |
| **Qualidade** | testes Python, Playwright em desktop/mobile, verificação de build e CI no GitHub Actions |
| **Integridade de dados** | comportamento fail-closed, preservação de estado validado e proibição de editar snapshot gerado para “fazer a UI passar” |
| **Acessibilidade** | teclado, foco visível, alvos de toque, aumento de texto e suporte a `prefers-reduced-motion` |
| **Entrega** | branches/PRs rastreáveis, artifacts de sync, deploy por GitHub Pages e checagem de paridade entre fonte e superfície publicada |

**Portfolio signal:** civic-tech · data pipelines · domain modeling · provenance · testing · accessibility · CI/CD · product engineering

---

## Arquitetura

```text
FONTES PÚBLICAS
TSE · Câmara · ALES · outras fontes documentadas
        ↓
INGESTÃO / NORMALIZAÇÃO
scripts/sync-data.py
        ↓
SNAPSHOT FACTUAL
data/generated/
        ↓
EVIDÊNCIA CURADA
data/reference/topic-evidence.json
        ↓
CAMADA DE PRODUTO
busca · ficha · assuntos · comparação
        ↓
BUILD V6
Eleventy
        ↓
HTML / CSS / JS
GitHub Pages
```

A chave eleitoral usada para vínculo entre camadas é **`SQ_CANDIDATO`**. O sistema evita criar lógica específica por nome de candidatura.

Quando um transporte intermediário é necessário por limitação de acesso a uma fonte, **origem e transporte permanecem separados na proveniência**.

---

## Regras de integridade

Algumas regras são tratadas como contrato de engenharia, não como detalhe de interface:

```text
dado ausente            ≠ fato negativo
ocupação declarada      ≠ atividade atual confirmada
registro histórico      ≠ situação atual
proposta                ≠ entrega
quantidade de registros ≠ importância política
fonte secundária        ≠ fonte primária
falha de API            ≠ autorização para publicar vazio
```

Snapshots automáticos são gerados e auditados antes da integração. Falhas transitórias não podem apagar silenciosamente informação previamente validada.

O produto não implementa score, ranking, previsão eleitoral, “melhor candidato” ou recomendação de voto.

---

## Proveniência e evidência

A arquitetura separa quatro coisas que frequentemente são misturadas em produtos de dados:

1. **cadastro factual** — dados eleitorais e declaratórios;
2. **histórico institucional** — vínculos e atuação documentados;
3. **evidência temática** — proposta, declaração ou atuação com fonte individualizada;
4. **interface** — apresentação do que já foi normalizado e validado.

A ausência de evidência temática permanece uma lacuna de cobertura. Ela não é convertida automaticamente em “não possui proposta” ou “não se posicionou”.

Documentos centrais:

- [Metodologia](METODOLOGIA.md)
- [Governança de dados e produto](docs/GOVERNANCE.md)
- [Modelo de dados](docs/DATA_MODEL.md)
- [Evidência temática](docs/TOPIC_EVIDENCE.md)
- [Mapa do site](docs/SITE_MAP.md)

---

## Desenvolvimento assistido por IA

Ferramentas de IA são usadas no projeto como apoio de engenharia — por exemplo em implementação, revisão, investigação de falhas e automação.

Elas **não são tratadas como fonte factual nem como autoridade editorial**.

Direção de produto, metodologia, modelo de dados, regras de proveniência, critérios editoriais, decisões de publicação e aceite final permanecem sob responsabilidade da mantenedora. Mudanças materiais passam por branch, diff, testes e revisão rastreável no GitHub.

Essa separação é intencional: automação pode acelerar o trabalho sem substituir responsabilidade sobre o resultado.

---

## Stack

```text
DATA / PIPELINE   Python · JSON · normalização determinística
FRONTEND          Eleventy · JavaScript · HTML · CSS
TESTES            unittest · Playwright
CI / DELIVERY     GitHub Actions · GitHub Pages
QUALIDADE         build verification · snapshot audit · provenance checks
ARQUITETURA       source-first · fail-closed · issue/PR-driven delivery
```

Nenhum framework JavaScript é enviado ao navegador pela camada V6; Eleventy é usado no build e a saída publicada permanece estática.

---

## Rodando localmente

Requisitos: Node.js compatível com o projeto e Python 3.

```bash
npm ci
npm start
```

Build e verificação:

```bash
npm run build
npm run verify
npm run test:e2e
python -m unittest discover -s tests -p 'test_*.py'
```

O pipeline eleitoral possui dependências e fontes externas próprias; consulte a documentação antes de executar sincronizações ou alterar `data/generated/`.

---

## Estrutura do repositório

```text
src/                  fonte da interface V6
styles/               CSS publicado
js/                   JavaScript publicado
data/generated/       snapshots eleitorais gerados
data/reference/       taxonomias e evidência curada
scripts/              sync, auditoria e geração
tests/                testes de dados e contratos
tests-e2e/            testes de interface com Playwright
docs/                 arquitetura, produto, operação e auditoria
.github/workflows/    CI e automações
```

Para contribuir ou operar a base, comece por [AGENTS.md](AGENTS.md) e [docs/GOVERNANCE.md](docs/GOVERNANCE.md). O estado executável do trabalho vive nas Issues e PRs; o README descreve o produto e a arquitetura estável.

---

## Autoria e desenvolvimento

**Quem Votar?** é idealizado e mantido por **Dra. Joyce Radis**.

O projeto combina definição de produto, metodologia de dados, desenho editorial, engenharia de software e desenvolvimento assistido por ferramentas de IA. A autoria não é atribuída à ferramenta: decisões, contratos, critérios de aceite e responsabilidade sobre o que é publicado permanecem humanos.

---

## Licença e independência

O software original é distribuído sob **GNU AGPL v3.0 only (`AGPL-3.0-only`)**. Dados, documentos, fotografias e outros materiais provenientes de terceiros permanecem sujeitos aos direitos e termos das respectivas fontes.

A licença do software não concede direito de uso do nome, identidade visual ou sinais distintivos do **Quem Votar?**, nem autorização para sugerir endosso institucional, político ou comercial.

O projeto é gratuito para consulta. Apoio financeiro não altera fontes, metodologia, ordem, critérios de evidência ou apresentação de candidaturas.

[Apoiar o projeto](apoio.html) · [GitHub Sponsors](https://github.com/sponsors/joyceradis)
