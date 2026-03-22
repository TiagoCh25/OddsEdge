# Configuracao

## Arquivos de ambiente

Ordem de carregamento:

1. variaveis ja existentes no processo
2. `.env`
3. `.env.<APP_ENV>`

Arquivos modelo:

- `.env.example`
- `.env.local.example`
- `.env.prd.example`

## Variaveis obrigatorias para dados reais

- `API_FOOTBALL_KEY`
- `THE_ODDS_API_KEY`

## Variaveis principais

### Ambiente e servidor

- `APP_ENV`: `local` ou `prd`
- `SERVER_HOST`: host da aplicacao
- `SERVER_PORT`: porta da aplicacao
- `PORT`: porta fornecida por cloud quando existir

### Rede

- `REQUESTS_TRUST_ENV`: respeita ou ignora proxy do sistema

### Dados e persistencia

- `USE_SAMPLE_DATA`: usa dados ficticios
- `PERSISTIR_EM_BANCO`: liga ou desliga persistencia SQLite
- `DATA_DIR`: diretorio base para JSON e historico
- `DIRETORIO_BANCO`: diretorio do banco SQLite
- `NOME_ARQUIVO_BANCO`: nome do arquivo `.db`

### Acesso inicial

- `ADMIN_NOME_INICIAL`: nome do admin inicial
- `ADMIN_EMAIL_INICIAL`: email do admin inicial
- `ADMIN_SENHA_INICIAL`: senha do admin inicial
- `AUTH_COOKIE_NAME`: nome do cookie de sessao autenticada
- `AUTH_SESSION_DURATION_HOURS`: duracao da sessao autenticada em horas
- `AUTH_COOKIE_SECURE`: envia o cookie autenticado apenas em HTTPS quando `true`

No ambiente `local`, se essas variaveis nao forem definidas, o projeto usa por padrao:

- `ADMIN_NOME_INICIAL=Admin`
- `ADMIN_EMAIL_INICIAL=tiagoch25@gmail.com`
- `ADMIN_SENHA_INICIAL=admin123`

Em ambientes nao locais, o recomendado e definir explicitamente essas variaveis no processo ou no arquivo `.env.<APP_ENV>`.

### Pipeline e operacao

- `SKIP_PIPELINE_ON_START`: sobe apenas a web
- `ENABLE_IDLE_SHUTDOWN`: desliga automatico ao ficar sem sessoes
- `IDLE_SHUTDOWN_SECONDS`: timeout do desligamento local
- `HEALTH_API_CACHE_SECONDS`: cache do `/health` para checagem das APIs externas

### API-Football

- `API_FOOTBALL_KEY`
- `API_FOOTBALL_FALLBACK_KEYS`
- `API_FOOTBALL_AUTH_MODE`: `apisports` ou `rapidapi`
- `API_FOOTBALL_HOST`
- `API_FOOTBALL_BASE_URL`
- `API_FOOTBALL_FREE_PLAN_MAX_SEASON`

### The Odds API

- `THE_ODDS_API_KEY`
- `THE_ODDS_BASE_URL`
- `THE_ODDS_REGIONS`
- `THE_ODDS_MARKETS`
- `ODDS_SPORTS`
- `ODDS_ONLY_ACTIVE_SPORTS`
- `ODDS_DYNAMIC_TOP_N`
- `ODDS_PRIORITY_SPORTS`
- `ODDS_MAX_SPORTS_PER_RUN`
- `ODDS_PREFERRED_BOOKMAKERS`: lista de bookmakers preferenciais suportados pela fonte atual
- `ODDS_RELEVANT_BOOKMAKERS`: lista completa de casas relevantes priorizadas na selecao exibida ao usuario

### Regras de recomendacao

- `MIN_PROBABILITY`
- `MIN_EV`
- `LEAGUE_GOAL_AVG`
- `MAX_POISSON_GOALS`

## Exemplos

### Ambiente local

```dotenv
APP_ENV=local
API_FOOTBALL_KEY=...
THE_ODDS_API_KEY=...
SERVER_PORT=8000
ENABLE_IDLE_SHUTDOWN=true
ADMIN_NOME_INICIAL=Admin
ADMIN_EMAIL_INICIAL=tiagoch25@gmail.com
ADMIN_SENHA_INICIAL=admin123
AUTH_COOKIE_NAME=oddsedge_auth
AUTH_SESSION_DURATION_HOURS=168
AUTH_COOKIE_SECURE=false
ODDS_MAX_SPORTS_PER_RUN=2
ODDS_PREFERRED_BOOKMAKERS=pinnacle,betfair_ex_eu,betfair_sb_uk,betway,onexbet
ODDS_RELEVANT_BOOKMAKERS=pinnacle,bet365,betfair,betano,sportingbet,betway,novibet,1xbet,parimatch,kto,pixbet,estrelabet,betnacional,aposta ganha,bodog,galera.bet,esportivabet
```

### Ambiente de producao

```dotenv
APP_ENV=prd
API_FOOTBALL_KEY=...
THE_ODDS_API_KEY=...
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
ENABLE_IDLE_SHUTDOWN=false
DATA_DIR=/app/runtime
DIRETORIO_BANCO=/app/runtime
ADMIN_NOME_INICIAL=Admin
ADMIN_EMAIL_INICIAL=admin@suaempresa.com
ADMIN_SENHA_INICIAL=trocar-antes-de-subir
AUTH_COOKIE_NAME=oddsedge_auth
AUTH_SESSION_DURATION_HOURS=168
AUTH_COOKIE_SECURE=true
```
