# Quem Votar? — Espírito Santo 2026

Consulte candidaturas, leia propostas e compare informações com fontes para decidir seu voto. O projeto existe para ser útil **antes da eleição, inclusive agora**.

**[Acesse o site](https://joyceradis.github.io/Quem-Votar/)** · [Como funciona](https://joyceradis.github.io/Quem-Votar/sobre.html) · [Metodologia](METODOLOGIA.md) · [Apoiar](https://joyceradis.github.io/Quem-Votar/apoio.html)

## O que está disponível

A **V6 está publicada** no link oficial. A versão do software está em [VERSION](VERSION).

O recorte público documentado cobre **Deputado Federal e Deputado Estadual do Espírito Santo nas eleições de 2026**. Expansões de cargo só passam a integrar este recorte quando estiverem disponíveis e verificadas na interface pública.

Você pode:

- buscar por nome ou número e filtrar por cargo, partido e assunto documentado;
- consultar a ficha com atuação atual confirmada, propostas/declarações, histórico e fontes;
- comparar até três candidaturas lado a lado;
- compartilhar fichas por URL;
- consultar bens, redes sociais e registros institucionais quando disponíveis.

A Home oferece caminhos por candidatura, assunto e comparação. Na ficha, a leitura principal segue **HOJE → PROPÕE → IMPACTO**, com histórico, dados eleitorais e fontes em profundidade.

## Como tratamos a informação

- Nenhum ranking, nota, vencedor ou recomendação de voto.
- Ocupação declarada ao TSE é dado secundário; não comprova atuação atual nem gera associação temática.
- Atuação histórica não vira promessa. PROPÕE e IMPACTO usam evidência prospectiva elegível.
- Uma lacuna permanece lacuna até existir fonte identificável e vínculo justificável.
- As afirmações preservam fonte, data e tipo de evidência.
- A identidade eleitoral usa `SQ_CANDIDATO`; vínculos entre bases são conservadores.

**Fontes principais:** TSE, Câmara dos Deputados e Assembleia Legislativa do Espírito Santo (ALES). Fontes declaratórias e secundárias são identificadas como tais. Evidência datada não é promovida automaticamente a situação atual.

Data e contagens são lidas de [data/generated/meta.json](data/generated/meta.json), com exibição no fuso `America/Sao_Paulo`. A evidência temática curada vive em [data/reference/topic-evidence.json](data/reference/topic-evidence.json), e a taxonomia em [data/reference/policy-topics.json](data/reference/policy-topics.json).

A coleta passa por staging, validação e revisão antes da promoção explícita à base canônica. Consulte [TOPIC_EVIDENCE](docs/TOPIC_EVIDENCE.md) para o contrato completo.

## Documentação e contribuição

| Preciso entender… | Onde consultar |
|---|---|
| O produto e suas fontes | Este README e [Metodologia](METODOLOGIA.md) |
| Onde fica cada documento | [Índice da documentação](docs/README.md) |
| Regras para alterar o projeto | [AGENTS.md](AGENTS.md) e [Governança](docs/GOVERNANCE.md) |
| Trabalho em andamento e decisões recentes | [Issues](https://github.com/joyceradis/Quem-Votar/issues) e [PRs](https://github.com/joyceradis/Quem-Votar/pulls), incluindo seus comentários posteriores |
| Arquitetura e histórico da V6 | [REBUILD_V6](docs/REBUILD_V6.md) |
| Como contribuir | [CONTRIBUTING](.github/CONTRIBUTING.md) |

Antes de iniciar trabalho, confira a unidade existente, seu responsável e as decisões posteriores ao texto inicial. Um checkpoint datado é histórico; não substitui o estado atual do código, da publicação ou da issue.

Este README apresenta o produto estável. A fila de execução permanece nas issues e PRs; contagens e estados transitórios não são duplicados aqui.

## Licenciamento

O software original deste repositório é distribuído sob a **GNU Affero General Public License v3.0 only (AGPL-3.0-only)**. Consulte [LICENSE](LICENSE).

A licença do software não transforma automaticamente dados, documentos, fotografias ou outros materiais de terceiros em conteúdo AGPL. Esses materiais permanecem sujeitos aos direitos, termos e condições das respectivas fontes.

A identidade visual e o nome do projeto não devem ser interpretados como autorização para sugerir endosso institucional, político ou comercial por parte do projeto ou de sua mantenedora.


### Software Licensing and Trademark Use

The AGPL-3.0-only license applies to the original software identified in this repository. It does not grant authorization to use the “Quem Votar?” name, logos, trademarks or other distinctive signs, nor to imply endorsement, association or partnership with the project or its maintainer.

Third-party data, documents, photographs and other materials remain subject to the licenses, rights and terms of their respective sources.

Detailed rules for visual assets and trademark usage may be documented separately in a future `TRADEMARK_POLICY.md`.


## Apoie o projeto

O **Quem Votar?** é gratuito para quem consulta e open source. Contribuições ajudam a custear manutenção, dados, documentação e infraestrutura sem conceder qualquer influência sobre o conteúdo eleitoral.

### GitHub Sponsors

O perfil **GitHub Sponsors** da mantenedora está ativo e público. O repositório usa `.github/FUNDING.yml` para exibir o botão nativo **Sponsor**.

[Apoiar via GitHub Sponsors](https://github.com/sponsors/joyceradis)

### PIX

Chave PIX (e-mail):

`contato@drajoyceradis.com`

Apoio financeiro não altera fontes, metodologia, temas, ordem, classificação ou apresentação de candidaturas.

Mais detalhes: [apoio e transparência](apoio.html) · [arquitetura de sustentabilidade](docs/SUSTAINABILITY.md).
