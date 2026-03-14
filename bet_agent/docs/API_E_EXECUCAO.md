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
- `data_source`
- `status`
- `error_message`
- `warning_message`
- `warning_details`

### `GET /health`

Retorna:

- `status`
- `app_env`
- `data_file`
- `data_file_exists`
- `ui_version`

### `POST /session/start`

Cria uma sessao de navegador para controle de idle shutdown.

### `POST /session/heartbeat`

Mantem a sessao ativa.

### `POST /session/end`

Encerra a sessao ativa.

## Comportamento especial do payload

- se o cache contiver dados ficticios antigos em modo real, a API marca erro
- se houver falha temporaria nas odds, o sistema pode reaproveitar a ultima recomendacao valida do mesmo dia
- o servidor tenta atualizar placares em background ao carregar o payload
