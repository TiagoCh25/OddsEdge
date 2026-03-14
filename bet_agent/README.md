# Bet Agent

Guia principal da aplicacao.

## Visao geral

O Bet Agent faz este fluxo:

1. busca jogos de futebol do dia
2. busca odds por liga
3. coleta estatisticas recentes dos times
4. calcula probabilidades com modelo de Poisson
5. calcula EV por mercado
6. filtra apostas recomendadas
7. salva cache atual em JSON
8. salva historico em SQLite
9. sobe a interface web em FastAPI

## Requisitos

- Python 3.10 ou superior
- chave da API-Football
- chave da The Odds API

## Instalacao

Dentro de `bet_agent`:

```bash
pip install -r requirements.txt
```

Para desenvolvimento:

```bash
pip install -r requirements-dev.txt
```

## Formas de executar

Pela raiz do projeto:

- `iniciar_bet_agent.bat`: pipeline + web local
- `iniciar_bet_agent_prd.bat`: simulacao de producao no Windows
- `iniciar_web_sem_api_8080.bat`: sobe apenas a interface sem consumir APIs

Direto em Python:

```bash
python main.py run-all
python main.py serve
python main.py pipeline
```

## Endpoints

- `GET /`: dashboard HTML
- `GET /bets`: payload atual com recomendacoes
- `GET /health`: healthcheck da aplicacao
- `POST /session/start`
- `POST /session/heartbeat`
- `POST /session/end`

## Persistencia

Por padrao, a aplicacao grava:

- `cache_matches.json`: estado atual da ultima execucao
- `history/YYYY/MM/DD/<execucao_id>.json`: historico por execucao
- `historico_apostas.db`: banco SQLite

Se `DATA_DIR` for definido, os arquivos acima passam a ser gravados nesse diretorio de runtime.

## Documentacao completa

- [Indice da documentacao](docs/README.md)
- [Guia para leigos](docs/GUIA_LEIGO.md)
- [Arquitetura](docs/ARQUITETURA.md)
- [Configuracao](docs/CONFIGURACAO.md)
- [Operacao local](docs/OPERACAO_LOCAL.md)
- [API e modos de execucao](docs/API_E_EXECUCAO.md)
- [Banco de dados](docs/BANCO_DE_DADOS.md)
- [Deploy em VPS](docs/DEPLOY_VPS.md)
- [Setup GitHub](docs/GITHUB_SETUP.md)
- [Publicar na web](docs/PUBLICAR_NA_WEB.md)
