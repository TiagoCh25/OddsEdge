# Bet Agent (Futebol + EV)

Aplicacao em Python para buscar jogos de futebol, estimar probabilidades com Poisson, calcular Expected Value (EV) e exibir apostas recomendadas em interface web.

## 1) Requisitos

- Python 3.10+
- Chaves de API:
  - API-Football
  - The Odds API

Guias completos:

- [Guia para leigos](docs/GUIA_LEIGO.md)
- [Publicar na web](docs/PUBLICAR_NA_WEB.md)

## 2) Instalacao

No diretorio `bet_agent`:

```bash
pip install -r requirements.txt
```

## 3) Configuracao das chaves

No PowerShell:

```powershell
$env:API_FOOTBALL_KEY="SUA_CHAVE_API_FOOTBALL"
$env:API_FOOTBALL_FALLBACK_KEYS="CHAVE_RESERVA_1,CHAVE_RESERVA_2"
$env:THE_ODDS_API_KEY="SUA_CHAVE_THE_ODDS_API"
```

Ou crie `bet_agent/.env` (carregado automaticamente):

```dotenv
API_FOOTBALL_KEY=SUA_CHAVE_API_FOOTBALL
API_FOOTBALL_FALLBACK_KEYS=CHAVE_RESERVA_1,CHAVE_RESERVA_2
THE_ODDS_API_KEY=SUA_CHAVE_THE_ODDS_API
```

`API_FOOTBALL_FALLBACK_KEYS` e opcional. O app usa essa(s) chave(s) apenas quando a chave principal atingir limite diario de requests.

Existe um modelo pronto: `.env.example`.

Perfis prontos:

- `.env.local.example` (ambiente local)
- `.env.prd.example` (producao)

O sistema carrega automaticamente:

1. `.env`
2. `.env.<APP_ENV>` (ex.: `.env.local` ou `.env.prd`)

Variaveis do sistema (painel do provedor/cloud) sempre tem prioridade.

### Modo de autenticacao da API-Football

- Conta no site API-Sports (direto):

```powershell
$env:API_FOOTBALL_AUTH_MODE="apisports"
```

- Conta via RapidAPI:

```powershell
$env:API_FOOTBALL_AUTH_MODE="rapidapi"
$env:API_FOOTBALL_HOST="v3.football.api-sports.io"
```

## 4) Variaveis opcionais

- `MIN_PROBABILITY` (default `0.65`)
- `MIN_EV` (default `0.0`)
- `APP_ENV` (default `local`; use `prd` em producao)
- `SERVER_HOST` (default `0.0.0.0`)
- `SERVER_PORT` (default `8000`)
- `REQUESTS_TRUST_ENV` (default `false`, ignora `HTTP_PROXY/HTTPS_PROXY` do sistema)
- `USE_SAMPLE_DATA` (default `false`)
- `PERSISTIR_EM_BANCO` (default `true`)
- `NOME_ARQUIVO_BANCO` (default `historico_apostas.db`)
- `DIRETORIO_BANCO` (opcional; por padrao usa `%TEMP%\\OddsEdge\\dados` no Windows)
- `API_FOOTBALL_FREE_PLAN_MAX_SEASON` (default `2024`, fallback para plano free)
- `API_FOOTBALL_FALLBACK_KEYS` (CSV opcional; usada somente quando `API_FOOTBALL_KEY` estourar limite diario)
- `IDLE_SHUTDOWN_SECONDS` (default `25`)
- `ENABLE_IDLE_SHUTDOWN` (default `true`; use `false` quando publicar na web)
- `ODDS_ONLY_ACTIVE_SPORTS` (default `true`, consulta apenas ligas dos jogos do dia quando possivel)
- `ODDS_DYNAMIC_TOP_N` (default `8`; com jogos em `x` ligas, usa `min(x, N)` pela prioridade configurada)
- `ODDS_PRIORITY_SPORTS` (lista CSV de prioridade das ligas populares)
- `ODDS_MAX_SPORTS_PER_RUN` (default `0`, sem limite; use `1`/`2`/`3` para economizar creditos)
- `ODDS_SPORTS` (lista CSV de ligas da The Odds API)
- `PORT` (usada automaticamente em cloud quando `SERVER_PORT` nao estiver definida)

Exemplo de modo economico:

```powershell
$env:ODDS_ONLY_ACTIVE_SPORTS="true"
$env:ODDS_MAX_SPORTS_PER_RUN="2"
$env:ODDS_SPORTS="soccer_italy_serie_a,soccer_spain_la_liga,soccer_epl,soccer_brazil_campeonato"
```

Se quiser forcar dados de exemplo para testes:

```powershell
$env:USE_SAMPLE_DATA="true"
```

## 5) Execucao

No diretorio `bet_agent`:

```bash
python main.py
```

Ou pela raiz do projeto:

```bat
iniciar_bet_agent.bat
```

Para modo producao (Windows/VM):

```bat
iniciar_bet_agent_prd.bat
```

Fluxo executado:

1. busca jogos do dia
2. busca odds
3. coleta estatisticas dos times
4. estima probabilidades (Poisson)
5. calcula EV
6. filtra apostas (`probabilidade > 65%` e `EV > 0`)
7. salva em `data/cache_matches.json`
8. persiste historico no banco SQLite (`data/historico_apostas.db`)
9. inicia servidor FastAPI

## 6) Interface web

Abra:

```text
http://localhost:8000
```

Endpoint JSON:

```text
GET /bets
```

## 7) Observacoes

- O sistema usa dados de exemplo apenas com `USE_SAMPLE_DATA=true`.
- O historico em banco e gravado por padrao em `%TEMP%\\OddsEdge\\dados\\historico_apostas.db` no Windows.
- Se quiser, defina `DIRETORIO_BANCO` para salvar em outro local.
- Tabelas criadas automaticamente:
  - `execucoes`
  - `partidas`
  - `odds_partidas`
  - `apostas_recomendadas`
- Sem chaves de API e com `USE_SAMPLE_DATA=false`, a aplicacao para com erro explicito.
- Com chave configurada, falhas de API agora geram erro explicito (nao cai silenciosamente em jogos fake).
- Ao fechar a ultima aba do `localhost:8000`, o servidor encerra automaticamente.
- Se `ENABLE_IDLE_SHUTDOWN=true`, o desligamento acontece por timeout (`IDLE_SHUTDOWN_SECONDS`).
- Em producao, use `APP_ENV=prd` e `ENABLE_IDLE_SHUTDOWN=false`.
- Estatisticas por time usam esta estrategia:
  1. tenta temporada atual com `last=10`
  2. se bloqueado, tenta temporada atual sem `last`
  3. se ainda bloqueado, tenta temporadas anteriores (mais recente liberada)
  4. se nao houver dados liberados, usa fallback interno e marca no JSON
- O arquivo `data/cache_matches.json` agora inclui:
  - `total_games_with_odds`
  - `stats_basis_by_match` (base estatistica usada por jogo)
- A selecao de ligas segue:
  1. detecta ligas com jogos ativos no dia
  2. ordena pela `ODDS_PRIORITY_SPORTS`
  3. aplica `ODDS_DYNAMIC_TOP_N` (se `x < N`, usa todas as `x`)
- Copa do Mundo ja esta preparada na configuracao (`soccer_fifa_world_cup`), ativando automaticamente quando houver jogos/odds.
- Mercados avaliados:
  - Over 1.5
  - Over 2.5
  - Under 3.5
  - Ambos marcam (BTTS)
  - Dupla chance (1X, X2, 12)
