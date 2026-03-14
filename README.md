# Bet Agent

Repositorio principal do projeto `bet_agent`.

## Objetivo

Aplicacao em Python para:

- buscar jogos de futebol do dia
- coletar odds em APIs externas
- estimar probabilidades com Poisson
- calcular EV
- exibir recomendacoes em interface web
- persistir historico em SQLite e JSON

## O que ja esta preparado

- repositorio Git local isolado
- CI no GitHub Actions
- Dockerfile e `docker-compose.yml`
- deploy base para VPS
- scripts `.bat` para uso local
- modo local sem consumo de API
- healthcheck HTTP
- documentacao tecnica e operacional

## Estrutura da raiz

- `bet_agent/`: codigo da aplicacao e documentacao principal
- `.github/workflows/`: pipeline CI/CD
- `ops/`: arquivos de apoio para VPS
- `Dockerfile`: imagem da aplicacao
- `docker-compose.yml`: stack local e producao com volume persistente
- `render.yaml`: alternativa de deploy no Render
- `iniciar_bet_agent.bat`: execucao local com pipeline completo
- `iniciar_bet_agent_prd.bat`: simulacao de producao
- `iniciar_web_sem_api_8080.bat`: interface sem consumir APIs

## Comeco rapido

1. Copie `bet_agent/.env.local.example` para `bet_agent/.env.local`.
2. Preencha as chaves de API.
3. Execute `iniciar_bet_agent.bat`.
4. Abra `http://localhost:8000`.

Modo sem consumir APIs:

1. Execute `iniciar_web_sem_api_8080.bat`.
2. Abra `http://localhost:8080`.

## Documentacao

- [README da aplicacao](bet_agent/README.md)
- [Indice da documentacao](bet_agent/docs/README.md)
- [Setup GitHub](bet_agent/docs/GITHUB_SETUP.md)
- [Deploy VPS](bet_agent/docs/DEPLOY_VPS.md)
