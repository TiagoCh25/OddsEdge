# Operacao Local

## Formas de subir

### Execucao normal

Use:

```bat
iniciar_bet_agent.bat
```

Esse script:

- entra em `bet_agent/`
- carrega `.env` e `.env.local`
- define defaults de economia de consumo
- executa pipeline + web
- abre o navegador quando os dados do dia estiverem disponiveis

### Simulacao de producao

Use:

```bat
iniciar_bet_agent_prd.bat
```

Esse modo:

- usa `APP_ENV=prd`
- desliga o idle shutdown
- aproxima o comportamento de producao

### Modo sem consumir APIs

Use:

```bat
iniciar_web_sem_api_8080.bat
```

Esse script:

- define `SKIP_PIPELINE_ON_START=true`
- sobe apenas a interface
- usa porta `8080`

### Preview com dados sample

Para visualizar dashboard, placar e melhores casas sem consumir APIs reais:

```bash
cd bet_agent
set USE_SAMPLE_DATA=true
python -B main.py run-all
```

Esse modo:

- gera dados ficticios
- monta apostas com placar e casas simuladas alinhadas ao grupo preferencial de bookmakers
- permite validar a interface local sem gasto de quota

## Acesso local

- modo normal: `http://localhost:8000`
- modo web-only: `http://localhost:8080`

## Validacao local

### Testes

```bash
python -m pytest -q bet_agent/tests
```

### Lint

```bash
python -m ruff check --no-cache bet_agent
```

## Onde ficam os dados locais

Por padrao, o projeto usa um diretorio de runtime derivado de `TEMP` ou `LOCALAPPDATA`.

Arquivos principais:

- `cache_matches.json`
- `history/`
- `historico_apostas.db`

Se `DATA_DIR` for informado, esse caminho passa a ser a fonte oficial desses arquivos.
