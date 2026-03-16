# Bet Agent

Guia principal da aplicacao.

## Visao geral

O Bet Agent faz este fluxo:

1. busca jogos de futebol do dia
2. valida a disponibilidade da The Odds API antes das consultas pesadas
3. busca odds por liga
4. calcula probabilidades com modelo de Poisson
5. calcula EV por mercado
6. filtra apostas recomendadas
7. salva cache atual em JSON
8. salva historico em SQLite
9. sobe a interface web em FastAPI

Se a API-Football falhar, o pipeline para antes de consultar odds. Se a The Odds API falhar no pre-check, o sistema interrompe a execucao antes de consumir chamadas extras de estatisticas dos times.
Se um jogo especifico falhar ao montar estatisticas, ele e ignorado, o erro fica registrado e o restante da execucao continua normalmente.
O dashboard destaca placares ao vivo no proprio nome do confronto e mostra, em cada aposta, as 3 melhores casas por odd dentre as operadoras relevantes priorizadas no projeto.
O dashboard do cliente nao expoe botao de compartilhamento.

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
- `GET /health`: healthcheck da aplicacao e das APIs externas
- `POST /session/start`
- `POST /session/heartbeat`
- `POST /session/end`

No payload de cada aposta, quando disponivel:

- `best_bookmakers`: lista das ate 3 melhores casas por odd do mercado, com link para a homepage quando houver mapeamento
- `best_bookmakers[].logo_url`: favicon/logo leve da casa quando houver mapeamento

Por padrao, o projeto considera a lista de casas relevantes definida no projeto e, quando pelo menos uma delas aparece na resposta, prioriza esse grupo na exibicao e na selecao das melhores odds.

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
