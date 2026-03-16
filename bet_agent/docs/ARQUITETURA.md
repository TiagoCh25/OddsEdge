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
3. `OddsAPI` executa um pre-check leve para validar disponibilidade e credito.
4. `OddsAPI` busca odds das ligas selecionadas.
5. `ProbabilityService` calcula `lambda_home` e `lambda_away`.
6. `PoissonModel` gera probabilidades por mercado.
7. `BetEvaluator` calcula EV e filtra recomendacoes.
8. O pipeline anexa as 3 melhores casas por mercado a cada aposta recomendada.
9. O payload atual e salvo em `cache_matches.json`.
10. Um snapshot historico e salvo em `history/YYYY/MM/DD/`.
11. O resultado e persistido no SQLite.
12. `web.server` expoe a interface e o endpoint `/bets`.

## Modos de execucao

- `run-all`: executa pipeline e sobe a web
- `serve`: sobe apenas a web
- `pipeline`: executa apenas a coleta e o processamento

## Estrategias importantes

### Consumo de APIs

- selecao dinamica de ligas por `ODDS_ONLY_ACTIVE_SPORTS`
- limite por `ODDS_MAX_SPORTS_PER_RUN`
- tentativa inicial com `ODDS_PREFERRED_BOOKMAKERS` para focar em casas mais relevantes suportadas
- filtro final por `ODDS_RELEVANT_BOOKMAKERS` para privilegiar a lista de casas relevantes do produto
- fallback de chaves para API-Football
- fail-fast: se a API-Football falhar, a Odds nao e consultada; se a The Odds API falhar no pre-check, o sistema nao consome chamadas adicionais de estatisticas
- aproveita a resposta ja retornada pela The Odds API para listar as 3 melhores casas por odd, sem chamadas extras

### Resiliencia

- reaproveita recomendacoes validas do dia quando ha falha temporaria de odds
- persiste historico local por JSON e SQLite
- usa `healthcheck` para operacao em container e VPS
- expoe saude agregada das APIs externas em `/health` com cache curto
- isola erro por partida: registra o problema e ignora apenas o jogo afetado

### Operacao local

- pode desligar automaticamente ao fechar a ultima aba
- possui modo web-only para nao consumir APIs

## Estrutura de arquivos relevante

- `main.py`: entrypoint da aplicacao
- `app/config.py`: configuracao central via variaveis de ambiente
- `app/main.py`: pipeline diario e CLI simples
- `web/server.py`: API web e dashboard
- `db/repositorio_historico.py`: schema e persistencia SQLite
