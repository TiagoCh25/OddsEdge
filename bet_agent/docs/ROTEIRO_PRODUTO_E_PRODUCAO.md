# Roteiro de Profissionalizacao + Plano de Evolucao

Observacao:

Este documento e um roteiro de evolucao e planejamento.
Ele nao substitui a documentacao operacional atual do projeto.

Para o estado real da aplicacao, use:

- `README.md`
- `docs/README.md`
- `docs/BANCO_DE_DADOS.md`
- `docs/DEPLOY_VPS.md`

---

## 1) Objetivo
Este documento junta:
- roteiro estrategico para levar o app para nivel de mercado
- plano de implementacao em tarefas executaveis (estilo backlog/issues)
- passos para historico de dados em banco NoSQL
- passos para publicar na web com operacao estavel

Escopo: documento de planejamento e evolucao futura.

---

## 2) Diagnostico atual (estado do projeto)

### Pontos fortes
- Arquitetura modular boa (`api/`, `services/`, `models/`, `web/`).
- Modelo estatistico implementado e regras de EV claras.
- Configuracao por ambiente (`.env*`) estruturada.
- Interface web funcional.
- Persistencia local em SQLite e historico em JSON.
- Docker, CI e guia de deploy inicial ja disponiveis.

### Gaps para nivel mais avancado
1. Testes de integracao com mocks ainda podem crescer.
2. Observabilidade ainda e basica.
3. Banco servidor pode ser considerado no futuro se houver crescimento maior.
4. Backup automatizado ainda depende da operacao da VPS.

---

## 3) Direcao tecnica

## Recomendacao
Manter Python no nucleo do produto.

Motivos:
- dominio de dados e estatistica favorece Python
- menor custo de evolucao
- stack atual ja entrega o objetivo do produto

---

## 4) Arquitetura alvo (resumo)

1. ingestao de jogos e odds
2. avaliacao probabilistica e EV
3. persistencia historica
4. exposicao via API e dashboard
5. operacao via CI, Docker e VPS

---

## 5) Proximas evolucoes sugeridas

- ampliar testes automatizados
- adicionar monitoramento e alertas
- evoluir dashboard historico
- avaliar banco servidor quando houver necessidade real
- estruturar backup restauravel e observabilidade
