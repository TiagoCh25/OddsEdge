# Arquitetura

## Visao geral

O Bet Agent e uma aplicacao Python orientada a pipeline diario com camada web.

Componentes principais:

- `api/`: integracao com API-Football e The Odds API
- `models/`: modelo estatistico de Poisson
- `services/`: regras de negocio para probabilidade e avaliacao de apostas
- `db/`: persistencia historica em SQLite
- `web/`: FastAPI, templates e arquivos estaticos
- `app/`: configuracao central e orquestracao do pipeline

## Fluxo principal

1. `app.main.run_daily_pipeline()` inicia a execucao.
2. `FootballAPI` busca os jogos do dia.
3. `OddsAPI` busca odds das ligas selecionadas.
4. `ProbabilityService` calcula `lambda_home` e `lambda_away`.
5. `PoissonModel` gera probabilidades por mercado.
6. `BetEvaluator` calcula EV e filtra recomendacoes.
7. O payload atual e salvo em `cache_matches.json`.
8. Um snapshot historico e salvo em `history/YYYY/MM/DD/`.
9. O resultado e persistido no SQLite.
10. `web.server` expoe a interface e o endpoint `/bets`.

## Modos de execucao

- `run-all`: executa pipeline e sobe a web
- `serve`: sobe apenas a web
- `pipeline`: executa apenas a coleta e o processamento

## Estrategias importantes

### Consumo de APIs

- selecao dinamica de ligas por `ODDS_ONLY_ACTIVE_SPORTS`
- limite por `ODDS_MAX_SPORTS_PER_RUN`
- fallback de chaves para API-Football

### Resiliencia

- reaproveita recomendacoes validas do dia quando ha falha temporaria de odds
- persiste historico local por JSON e SQLite
- usa `healthcheck` para operacao em container e VPS

### Operacao local

- pode desligar automaticamente ao fechar a ultima aba
- possui modo web-only para nao consumir APIs

## Estrutura de arquivos relevante

- `main.py`: entrypoint da aplicacao
- `app/config.py`: configuracao central via variaveis de ambiente
- `app/main.py`: pipeline diario e CLI simples
- `web/server.py`: API web e dashboard
- `db/repositorio_historico.py`: schema e persistencia SQLite
