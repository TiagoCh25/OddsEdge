# Publicar o Bet Agent na Web (passo a passo)

Este guia mostra como deixar o sistema online, para abrir por link e nao apenas no seu PC.

## Opcao recomendada para comecar: Render

E a forma mais simples para quem nao quer configurar servidor manual.

O repositorio ja inclui um arquivo pronto `render.yaml` na raiz do projeto.

## 1) Preparar o projeto

1. Suba o projeto em um repositorio GitHub.
2. Garanta que o projeto tenha:
   - `requirements.txt`
   - `main.py`
   - este app ja usa `0.0.0.0` e porta por variavel (ok para cloud)

## 2) Criar servico no Render

1. Acesse o Render e conecte seu GitHub.
2. Clique em `New +` -> `Web Service`.
3. Selecione o repositorio.
4. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python -B main.py`
   - Root Directory: `bet_agent` (importante)

Se quiser, use o `Blueprint` do Render com o `render.yaml`.

## 3) Variaveis de ambiente no Render

Adicione estas variaveis:

- `API_FOOTBALL_KEY`
- `THE_ODDS_API_KEY`
- `API_FOOTBALL_AUTH_MODE=apisports`
- `REQUESTS_TRUST_ENV=false`
- `USE_SAMPLE_DATA=false`
- `ENABLE_IDLE_SHUTDOWN=false`
- `APP_ENV=prd`
- `ODDS_ONLY_ACTIVE_SPORTS=true`
- `ODDS_MAX_SPORTS_PER_RUN=2`
- `ODDS_SPORTS=soccer_italy_serie_a,soccer_spain_la_liga,soccer_epl,soccer_brazil_campeonato`

Observacao:

- `ENABLE_IDLE_SHUTDOWN=false` evita que o servidor desligue por falta de abas locais.
- `APP_ENV=prd` ativa padrao de producao na configuracao.

## 4) Deploy

1. Clique em `Create Web Service`.
2. Aguarde build/deploy finalizar.
3. Abra a URL publica fornecida pelo Render.

## 5) Se quiser dominio proprio

No Render:

1. abra o servico
2. menu `Settings` -> `Custom Domains`
3. siga o DNS informado (CNAME/A)

## 6) Boas praticas de operacao

- nunca subir chave de API no codigo
- usar apenas variaveis de ambiente
- revisar consumo de creditos da The Odds API
- reduzir ligas com `ODDS_MAX_SPORTS_PER_RUN`

## 7) Atualizacao diaria dos jogos

O pipeline roda no startup do app.

Para garantir dados sempre renovados:

- faca um redeploy diario (ou restart agendado da aplicacao)

Em muitos provedores isso pode ser feito com job agendado ou deploy hook.

## 8) Problemas comuns

1. "Sem jogos" ou "Falha temporaria":
   - verificar creditos da The Odds API
   - verificar chaves no painel da cloud
2. Erro de porta:
   - manter `SERVER_PORT` vazio e deixar o provedor controlar `PORT`
3. App "dorme":
   - em planos gratuitos isso e normal
