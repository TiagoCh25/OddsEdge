# API e Modos de Execucao

## Modos de execucao

### `python main.py run-all`

- executa o pipeline
- grava JSON atual
- grava historico
- persiste em SQLite
- inicializa de forma idempotente a base de acesso e o admin inicial ao subir a web
- sobe a web

### `python main.py serve`

- sobe apenas a web
- inicializa de forma idempotente a base de acesso e o admin inicial
- nao executa pipeline na inicializacao

### `python main.py pipeline`

- executa apenas o pipeline
- nao sobe servidor web
- faz pre-check da The Odds API antes de consultar odds e estatisticas pesadas

## Endpoints

### `GET /`

Retorna a landing page comercial publica quando nao ha sessao autenticada.

Se o usuario ja estiver autenticado, a rota redireciona para `GET /dashboard`.

### `GET /planos`

Retorna a landing comercial com foco na secao de planos. Pode ser usada como destino de CTAs de upgrade sem redirecionar usuarios autenticados para o dashboard.

### `GET /dashboard`

Retorna o dashboard HTML autenticado.

### `GET /bets`

Retorna o payload atual filtrado pelo perfil/plano do usuario autenticado.

Regras de exibicao:

- `gratis`: recebe apenas 1 recomendacao elegivel por dia, com odd minima `1.30`, inicio futuro e pelo menos 1 hora de antecedencia
- `pro`: recebe todas as recomendacoes validas do momento
- `admin`: recebe todas as recomendacoes validas do momento

O payload inclui metadados extras para o frontend comunicar o estado da tela do dashboard, como:

- `dashboard_estado`
- `dashboard_mensagem`
- `dashboard_mensagem_auxiliar`
- `dashboard_mostrar_upgrade`

Tambem retorna os campos usuais:

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

### `GET /login`

Retorna a tela HTML de login.

### `POST /auth/login`

Processa login por formulario HTML, valida email e senha, atualiza `ultimo_login_em`, cria uma sessao em `sessoes_usuario` e envia um cookie HTTPOnly para o navegador.

### `GET /cadastro`

Retorna a tela HTML de cadastro.

### `POST /auth/cadastro`

Processa cadastro por formulario HTML, valida nome, email e senha, persiste o usuario com `perfil=usuario`, `plano=gratis` e `status=ativo`, e redireciona para a tela de login.

### `GET /esqueci-senha`

Retorna a tela HTML para solicitar recuperacao de senha.

### `POST /auth/esqueci-senha`

Processa o pedido de recuperacao por email, gera um token unico com expiracao e envia o link por email ou salva em arquivo local conforme configuracao.

### `GET /redefinir-senha`

Retorna a tela HTML de redefinicao de senha a partir de um token valido.

### `POST /auth/redefinir-senha`

Valida o token de recuperacao, salva a nova senha em hash seguro, invalida o token e encerra sessoes antigas do usuario.

### `POST /auth/logout`

Invalida a sessao autenticada atual no banco, remove o cookie do navegador e redireciona para `GET /login`.

### `GET /admin`

Retorna a tela HTML da area admin inicial. Exige usuario autenticado com `perfil=admin`.

### `POST /admin/usuarios/{id}/plano`

Atualiza o plano do usuario entre `gratis` e `pro`. Exige `perfil=admin`.

### `POST /admin/usuarios/{id}/status`

Atualiza o status do usuario entre `ativo` e `bloqueado`. Exige `perfil=admin`.

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
- o dashboard HTML e os endpoints usados pela interface autenticada passam a exigir sessao valida
- quando a sessao expira, o frontend redireciona o usuario para `GET /login`
