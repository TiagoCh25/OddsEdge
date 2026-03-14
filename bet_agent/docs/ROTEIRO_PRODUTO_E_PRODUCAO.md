# Roteiro de Profissionalizacao + Plano de Implementacao (OddsEdge)

## 1) Objetivo
Este documento junta:
- roteiro estrategico para levar o app para nivel de mercado
- plano de implementacao em tarefas executaveis (estilo backlog/issues)
- passos para historico de dados em banco NoSQL
- passos para publicar na web com operacao estavel

Escopo: nao executar mudancas automaticamente. Documento de planejamento e execucao guiada.

---

## 2) Diagnostico atual (estado do projeto)

### Pontos fortes
- Arquitetura modular boa (`api/`, `services/`, `models/`, `web/`).
- Modelo estatistico implementado e regras de EV claras.
- Configuracao por ambiente (`.env*`) ja estruturada.
- Interface web funcional e evoluindo bem.

### Gaps para nivel "producao"
1. Testes automatizados insuficientes (unit + integracao).
2. Persistencia historica fraca (snapshot unico em JSON).
3. Acoplamento entre pipeline e inicializacao da web.
4. Observabilidade limitada (logs estruturados, metricas, alertas).
5. CI/CD inexistente.
6. Hardening e operacao de servidor ainda nao implementados.

---

## 3) Stack: Python ou C#?

## Recomendacao
Manter **Python** no nucleo do produto.

Motivos:
- Dominio do problema (analytics/estatistica/data APIs) favorece Python.
- Ecossistema forte para modelagem, ETL e experimentacao rapida.
- Menor custo de evolucao no curto e medio prazo.

Quando considerar C#:
- Exigencia corporativa forte de stack .NET em toda empresa.
- Integracoes internas obrigatorias em ecossistema Microsoft.

Diretriz pratica:
- Python para core analitico e API.
- Se necessario no futuro, criar gateway/service adicional sem migrar o core.

---

## 4) Arquitetura alvo (resumo)

1. **Ingestao**: coleta jogos + odds + stats.
2. **Avaliacao**: probabilidade + EV + filtros de recomendacao.
3. **Persistencia**:
   - curto prazo: JSON historico por execucao
   - medio prazo: NoSQL (CouchDB recomendado)
4. **Exposicao**:
   - API web (FastAPI)
   - UI dashboard
   - aba nova de historico
5. **Operacao**:
   - agendamento pipeline
   - monitoramento, backup, alertas

---

## 5) Banco NoSQL (gratis e licenca)

## Recomendado
**Apache CouchDB**
- JSON nativo
- licenca Apache 2.0
- uso local gratuito
- bom para historico de documentos por execucao

Alternativas
- MongoDB Community (gratis, licenca SSPL)
- MongoDB Atlas free tier (gratuito com limites)

---

## 6) Modelagem de dados historicos (MVP)

## Colecoes/documentos
1. `runs`
- `run_id`, `generated_at`, `status`, `totals`, `config_snapshot`

2. `fixtures_raw`
- payload bruto da API-Football por run

3. `odds_raw`
- payload bruto da The Odds API por run/sport

4. `recommendations`
- uma linha por aposta recomendada (`run_id + fixture_id + market`)

5. `outcomes`
- resultado final da aposta apos fechamento do jogo

6. `rejected_candidates` (forte recomendacao)
- apostas nao recomendadas + motivo (`prob_below_min`, `ev_non_positive`, etc.)

## Chaves de idempotencia
- recomendacao: `run_id + fixture_id + market`
- fixture: `fixture_id + run_id`

---

## 7) Publicacao na web (VPS)

## Infra recomendada
- VPS Linux (Ubuntu LTS)
- Nginx + FastAPI/Uvicorn
- systemd para servico web e job de pipeline
- SSL Let’s Encrypt

## Fluxo de deploy
1. Provisionar VPS e acesso SSH por chave.
2. Hardening (usuario nao-root + firewall).
3. Clonar repo, criar venv, instalar deps.
4. Configurar `.env` de producao.
5. Criar servico systemd para API.
6. Criar timer/cron para pipeline.
7. Configurar Nginx reverse proxy.
8. Configurar dominio + HTTPS.
9. Ativar backup diario (dados + banco).

---

## 8) Roadmap por fases

## Fase A - Fundacao tecnica (1 semana)
- Git workflow, qualidade de codigo, testes basicos.

## Fase B - Historico e banco (1 a 2 semanas)
- Persistencia por run, ingestion NoSQL, settlement.

## Fase C - Deploy web (1 semana)
- VPS, servicos, HTTPS, monitoramento inicial.

## Fase D - Evolucao de produto (continuo)
- Aba historico, KPI de performance, automacao CI/CD.

---

## 9) Backlog de implementacao (estilo issues)

Escalas:
- Esforco: P (pequeno), M (medio), G (grande)
- Risco: Baixo, Medio, Alto

| ID | Tarefa | Fase | Prioridade | Esforco | Risco | Dependencias | Definicao de pronto |
|---|---|---|---|---|---|---|---|
| BE-001 | Padronizar Git flow (`main`, `develop`, PR template) | A | Alta | P | Baixo | nenhuma | fluxo documentado e usado |
| BE-002 | Adicionar `ruff`, `black`, `mypy` no projeto | A | Alta | P | Baixo | BE-001 | comandos de qualidade rodando local |
| BE-003 | Criar suite de testes unitarios (Poisson/EV/filtros) | A | Alta | M | Medio | BE-002 | cobertura minima para regras criticas |
| BE-004 | Criar testes de integracao com mocks de APIs | A | Alta | M | Medio | BE-003 | pipeline testavel sem consumir quota |
| BE-005 | Desacoplar start da web e pipeline (modo web-only oficial) | A | Alta | P | Baixo | nenhuma | app sobe sem rodar coleta |
| DA-001 | Persistir JSON por run em `data/history/YYYY/MM/DD` | B | Alta | P | Baixo | BE-005 | arquivos historicos por execucao |
| DA-002 | Salvar payload bruto de fixtures e odds por run | B | Alta | M | Medio | DA-001 | raw payload versionado por run |
| DA-003 | Salvar candidatos rejeitados + motivo | B | Media | M | Baixo | DA-001 | auditoria de selecao disponivel |
| DB-001 | Subir CouchDB local (dev) | B | Alta | P | Baixo | nenhuma | instancia acessivel localmente |
| DB-002 | Criar camada `repositories/` para persistencia | B | Alta | M | Medio | DB-001 | escrita/leitura desacoplada do service |
| DB-003 | Implementar ingestao idempotente (`run_id`/chaves) | B | Alta | M | Medio | DB-002 | sem duplicidade em reprocessamento |
| DB-004 | Implementar job de settlement de resultados | B | Alta | M | Medio | DB-003 | apostas encerradas com status final |
| API-001 | Endpoint de historico (`/history/summary`) | B | Media | M | Medio | DB-003 | resumo por periodo/liga/mercado |
| WEB-001 | Nova aba Historico no dashboard | D | Media | M | Medio | API-001 | filtros + tabela KPI historica |
| OPS-001 | Criar Dockerfile + compose para ambiente reproduzivel | A | Media | M | Medio | BE-002 | projeto sobe em container |
| OPS-002 | Provisionar VPS Ubuntu + hardening | C | Alta | M | Alto | nenhuma | acesso seguro e firewall ativo |
| OPS-003 | Configurar systemd (api + pipeline) | C | Alta | M | Medio | OPS-002 | servicos reiniciam automaticamente |
| OPS-004 | Configurar Nginx + dominio + HTTPS | C | Alta | M | Medio | OPS-003 | app publico com TLS |
| OPS-005 | Backups diarios (dados + banco) | C | Alta | M | Medio | DB-003, OPS-004 | restore testado com sucesso |
| OBS-001 | Logs estruturados com `run_id` | D | Media | P | Baixo | BE-005 | rastreabilidade de execucoes |
| OBS-002 | Monitoramento uptime + alerta falhas | D | Media | P | Baixo | OPS-004 | alerta ativo para indisponibilidade |
| SEC-001 | Revisao de segredo/env e politica de rotacao | D | Alta | P | Baixo | OPS-004 | segredos fora do codigo e rotacao definida |

---

## 10) Plano de execucao sugerido (30/60/90 dias)

## 0-30 dias
- Fase A completa.
- DA-001 e DA-002 concluidos.
- Resultado: qualidade minima, previsibilidade e historico em arquivos.

## 31-60 dias
- DB-001 ate DB-004.
- API-001 inicial.
- Resultado: historico em banco + settlement basico.

## 61-90 dias
- Fase C completa (deploy VPS + HTTPS + backup).
- OBS-001/OBS-002/SEC-001.
- Resultado: app operando na web com base profissional.

---

## 11) Checklist de Go-Live (producao)

- [ ] Testes unitarios e integracao passando
- [ ] Pipeline resiliente a quota excedida
- [ ] Persistencia historica ativa
- [ ] Backup diario testado (restore real)
- [ ] HTTPS ativo
- [ ] Logs estruturados e monitoramento ativo
- [ ] Chaves e segredos fora do repositorio
- [ ] Documentacao operacional (`DEPLOY.md` e `RUNBOOK.md`)

---

## 12) Proximos passos praticos (ordem recomendada)
1. Executar Fase A inteira.
2. Implementar DA-001/DA-002 imediatamente.
3. Subir CouchDB local e concluir DB-002/DB-003.
4. Publicar MVP em VPS com HTTPS.
5. Abrir epico da aba Historico (produto).

---

## 13) Observacoes finais
- O gargalo principal hoje e quota das APIs free.
- Com historico e fallback bem feitos, a UX para de "quebrar" quando faltar credito.
- Profissionalizacao vem mais de processo + operacao + observabilidade do que de trocar de linguagem.
