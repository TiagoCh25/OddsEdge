# API e Modos de Execucao

## Modos de execucao

### `python main.py run-all`

- executa o pipeline
- grava JSON atual
- grava historico
- persiste em SQLite
- sobe a web

### `python main.py serve`

- sobe apenas a web
- nao executa pipeline na inicializacao

### `python main.py pipeline`

- executa apenas o pipeline
- nao sobe servidor web
- faz pre-check da The Odds API antes de consultar odds e estatisticas pesadas

## Endpoints

### `GET /`

Retorna o dashboard HTML.

### `GET /bets`

Retorna o payload atual com:

- `generated_at`
- `scores_updated_at`
- `total_games_analyzed`
- `total_games_with_odds`
- `total_bets`
- `combined_odd_top2`
- `bets`
- `skipped_matches_count`
- `processing_errors`
- `data_source`
- `status`
- `error_message`
- `warning_message`
- `warning_details`

Cada item de `bets` pode incluir:

- `best_bookmakers`: ate 3 melhores casas por odd naquele mercado
- `best_bookmakers[].url`: homepage da casa quando o nome estiver mapeado
- `best_bookmakers[].logo_url`: logo/favicon da casa quando o nome estiver mapeado
- `home_goals` e `away_goals`: usados para exibir placar ao vivo e resultado final no nome do confronto

As melhores casas passam por uma priorizacao da lista de operadoras relevantes do projeto. Quando alguma delas aparece na resposta, o sistema restringe a selecao a esse grupo. Se nenhuma aparecer, entra fallback seguro.

### `GET /health`

Retorna:

- `status`
- `app_env`
- `data_file`
- `data_file_exists`
- `ui_version`
- `api_health.status`
- `api_health.checked_at`
- `api_health.cache_seconds`
- `api_health.dependencies.api_football`
- `api_health.dependencies.the_odds_api`

### `POST /session/start`

Cria uma sessao de navegador para controle de idle shutdown.

### `POST /session/heartbeat`

Mantem a sessao ativa.

### `POST /session/end`

Encerra a sessao ativa.

## Comportamento especial do payload

- se o cache contiver dados ficticios antigos em modo real, a API marca erro
- se houver falha temporaria nas odds, o sistema pode reaproveitar a ultima recomendacao valida do mesmo dia
- se a API-Football falhar, o pipeline aborta antes da etapa de odds
- se a The Odds API falhar no pre-check, o pipeline aborta antes de consultar estatisticas detalhadas dos times
- se um jogo falhar durante a coleta de estatisticas ou calculo, ele e ignorado e o restante segue
- o endpoint `/health` usa cache curto para nao consumir APIs em excesso
- o servidor tenta atualizar placares em background ao carregar o payload
- as casas sao ordenadas por odd descrescente; em empate, o sistema desempata por cobertura de mercados no jogo, depois por presenca da casa na rodada e por ultimo por ordem alfabetica
- a busca de odds tenta primeiro um conjunto preferencial de bookmakers suportados pela The Odds API antes de abrir fallback
- a vitrine final das casas considera a lista completa de casas relevantes definida no projeto
