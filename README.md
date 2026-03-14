# Bet Agent

Repositorio preparado para evolucao profissional do `bet_agent`, com foco em:

- versionamento isolado no GitHub
- execucao local com `.bat`
- modo local sem consumo de API
- CI no GitHub Actions
- deploy em VPS com Docker
- persistencia local em SQLite com volume dedicado

## Estrutura

- `bet_agent/`: aplicacao Python
- `.github/workflows/`: pipeline CI/CD
- `ops/`: arquivos de apoio para VPS
- `iniciar_bet_agent.bat`: execucao local com pipeline completo
- `iniciar_bet_agent_prd.bat`: simulacao de producao no Windows
- `iniciar_web_sem_api_8080.bat`: interface local sem consumir APIs

## Comeco rapido

1. Copie `bet_agent/.env.local.example` para `bet_agent/.env.local`.
2. Preencha as chaves de API.
3. Execute `iniciar_bet_agent.bat`.

Modo sem consumir APIs:

1. Execute `iniciar_web_sem_api_8080.bat`.
2. Abra `http://localhost:8080`.

## Docker / VPS

1. Copie `bet_agent/.env.prd.example` para `bet_agent/.env.prd`.
2. Ajuste as variaveis.
3. Rode `docker compose up -d --build`.

Healthcheck:

- `http://localhost:8000/health`

## GitHub

Guia recomendado:

- [Setup GitHub](bet_agent/docs/GITHUB_SETUP.md)
- [Deploy VPS](bet_agent/docs/DEPLOY_VPS.md)
- [README da aplicacao](bet_agent/README.md)
