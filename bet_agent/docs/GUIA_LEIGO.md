# Guia Rapido Para Leigos

## O que este sistema faz

O Bet Agent:

- busca jogos de futebol do dia
- busca odds das casas
- calcula probabilidades com matematica
- calcula EV
- mostra quais apostas parecem ter valor

Em resumo: ele tenta trocar decisao no achismo por decisao baseada em dados.

## O que voce precisa

- Python instalado
- chave da API-Football
- chave da The Odds API

## Como rodar no seu PC

1. Copie `.env.local.example` para `.env.local`.
2. Preencha as chaves.
3. Na raiz do projeto, execute:

```bat
iniciar_bet_agent.bat
```

4. Abra:

```text
http://localhost:8000
```

## Como abrir sem gastar credito de API

Use:

```bat
iniciar_web_sem_api_8080.bat
```

Depois abra:

```text
http://localhost:8080
```

## Onde os dados ficam salvos

O projeto grava:

- um JSON com o resultado atual
- um historico por execucao
- um banco SQLite com as tabelas do sistema

## Quando aparece falha temporaria

Normalmente isso significa:

- chave invalida
- limite da The Odds API atingido
- indisponibilidade temporaria da API

Quando possivel, o sistema reaproveita a ultima recomendacao valida do mesmo dia.

## O que e EV

EV significa valor esperado.

Formula:

```text
EV = (probabilidade x odd) - 1
```

- EV maior que 0: aposta com valor esperado positivo
- EV menor que 0: tende a ser ruim no longo prazo
