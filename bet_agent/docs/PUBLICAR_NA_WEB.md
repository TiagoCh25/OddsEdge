# Publicar na Web

Este guia cobre duas rotas:

- deploy simples em plataforma gerenciada
- deploy profissional em VPS

## Opcao 1: Render

Boa para colocar o projeto no ar rapidamente.

### Preparacao

1. Suba o projeto no GitHub.
2. Garanta que o Render use a pasta `bet_agent` como raiz.
3. Use o `render.yaml` ja incluido na raiz do repositorio.

### Configuracao esperada

- Build Command: `pip install -r requirements.txt`
- Start Command: `python -B main.py run-all`
- Root Directory: `bet_agent`

### Variaveis recomendadas

- `APP_ENV=prd`
- `ENABLE_IDLE_SHUTDOWN=false`
- `REQUESTS_TRUST_ENV=false`
- `USE_SAMPLE_DATA=false`
- `ODDS_ONLY_ACTIVE_SPORTS=true`
- `ODDS_MAX_SPORTS_PER_RUN=2`
- `ODDS_SPORTS=soccer_italy_serie_a,soccer_spain_la_liga,soccer_epl,soccer_brazil_campeonato`
- `API_FOOTBALL_KEY`
- `THE_ODDS_API_KEY`

### Observacao importante

Em plataforma gerenciada, o banco SQLite e util para MVP, mas o ideal para operacao duravel continua sendo usar volume persistente ou migrar no futuro para um banco servidor.

## Opcao 2: VPS

Esta e a rota recomendada para maior controle.

Passos resumidos:

1. clonar o repositorio na VPS
2. criar `bet_agent/.env.prd`
3. subir com `docker compose up -d --build`
4. configurar Nginx
5. configurar HTTPS
6. configurar timer do pipeline

Guia detalhado:

- [DEPLOY_VPS.md](DEPLOY_VPS.md)

## Boas praticas

- nunca commitar segredos
- usar apenas variaveis de ambiente
- manter `ENABLE_IDLE_SHUTDOWN=false` em producao
- revisar consumo da The Odds API
- testar `GET /health` apos cada deploy
