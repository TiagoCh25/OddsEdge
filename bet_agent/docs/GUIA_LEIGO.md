# Bet Agent - Guia Rapido Para Leigos

Este guia explica o projeto sem linguagem tecnica.

## 1) O que este sistema faz

O Bet Agent:

- busca os jogos de futebol do dia
- calcula probabilidades com modelo matematico (Poisson)
- compara com as odds
- calcula o EV (valor esperado)
- mostra recomendacoes com maior chance de valor

Em resumo: ele filtra apostas com base em estatistica, para evitar decisao no "achismo".

## 2) O que voce precisa para funcionar

- Python instalado (3.10+)
- chave da API-Football
- chave da The Odds API

Sem essas chaves, o sistema nao consegue buscar dados reais.

## 3) Como rodar localmente (no seu PC)

1. Entre na pasta `bet_agent`.
2. Instale dependencias:

```bash
pip install -r requirements.txt
```

3. Crie o arquivo `.env` (na pasta `bet_agent`) com suas chaves:

```dotenv
API_FOOTBALL_KEY=SUA_CHAVE_API_FOOTBALL
THE_ODDS_API_KEY=SUA_CHAVE_THE_ODDS_API
```

4. Na pasta raiz do projeto, execute:

```bat
iniciar_bet_agent.bat
```

5. Abra no navegador:

```text
http://localhost:8000
```

Se quiser simular modo producao em uma VM/servidor Windows:

```bat
iniciar_bet_agent_prd.bat
```

## 4) Entendendo a mensagem de "falha temporaria"

Se aparecer aviso sobre falha de odds, normalmente e por:

- chave invalida
- limite de creditos da The Odds API acabou
- indisponibilidade temporaria da API

Quando isso acontece, o sistema mostra as ultimas recomendacoes validas do dia.

## 5) Como economizar creditos da The Odds API

Use estas configuracoes no `.env`:

```dotenv
ODDS_ONLY_ACTIVE_SPORTS=true
ODDS_MAX_SPORTS_PER_RUN=2
ODDS_SPORTS=soccer_italy_serie_a,soccer_spain_la_liga,soccer_epl,soccer_brazil_campeonato
```

Explicando:

- `ODDS_ONLY_ACTIVE_SPORTS=true`: consulta so ligas que realmente tem jogos hoje
- `ODDS_MAX_SPORTS_PER_RUN=2`: limita quantas ligas serao consultadas por execucao
- `ODDS_SPORTS=...`: define ligas permitidas

Quanto menor o limite, menor o consumo de creditos.

## 6) O que significa EV

EV (Expected Value) e uma conta simples:

```text
EV = (probabilidade x odd) - 1
```

- EV maior que 0: aposta com valor esperado positivo
- EV menor que 0: tende a nao compensar no longo prazo
