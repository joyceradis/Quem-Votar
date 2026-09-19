# Arquitetura de sustentabilidade

## Objetivo

Permitir apoio financeiro ao desenvolvimento e à manutenção do Quem Votar? sem acoplar financiamento à camada editorial eleitoral.

A sustentabilidade é uma **camada operacional**. Ela não participa da seleção, interpretação, classificação ou publicação de evidências políticas.

## Fronteiras

```text
GitHub Sponsors / PIX
        │
        ▼
camada de sustentabilidade
README · apoio.html · FUNDING.yml
        │
        ╳  sem escrita / sem influência
        │
        ▼
núcleo eleitoral
dados · evidências · busca · temas · comparação · fichas
```

## Superfícies permitidas

- `.github/FUNDING.yml`;
- botão nativo do GitHub Sponsors;
- seção de apoio no README;
- `apoio.html`;
- chave PIX estática com cópia local;
- documentação pública de independência e financiamento;
- link secundário de apoio em rodapé.

## Superfícies proibidas

Apoio financeiro não pode aparecer como:

- banner em ficha de candidatura;
- anúncio dentro de busca;
- conteúdo patrocinado em temas;
- destaque em comparação;
- alteração de ordenação;
- selo de qualidade;
- prioridade editorial;
- personalização política;
- tracker publicitário.

## Dados e isolamento

A camada de sustentabilidade não lê nem grava:

- `data/reference/topic-evidence.json`;
- classificações temáticas;
- dados normalizados de candidaturas;
- resultados de comparação;
- ordenação de busca.

Nenhum valor de apoio entra no modelo de dados eleitoral.

## GitHub Sponsors

O repositório usa `.github/FUNDING.yml` com o perfil `joyceradis`.

A ativação final do GitHub Sponsors depende da configuração da conta da mantenedora. O repositório não armazena dados bancários, fiscais ou credenciais de pagamento.

## PIX

A chave PIX pública usada na página de apoio é:

`contato@drajoyceradis.com`

O botão de cópia usa apenas APIs locais do navegador. Não há SDK de pagamento, tracker, iframe ou dependência financeira de terceiros no site.

## Independência

Contribuições financiam manutenção de software, dados, documentação e infraestrutura.

Elas não concedem:

- veto;
- aprovação;
- acesso antecipado;
- alteração de metodologia;
- tratamento preferencial;
- destaque de candidatura;
- interferência na camada canônica de evidências.

A governança editorial aplicável permanece em [GOVERNANCE.md](GOVERNANCE.md).
