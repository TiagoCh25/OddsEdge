# Deploy VPS

## Stack recomendada

- Ubuntu 24.04 LTS
- Docker + Docker Compose
- Nginx
- systemd timer para pipeline

## Arquivos preparados

- `Dockerfile`
- `docker-compose.yml`
- `ops/nginx/bet-agent.conf.example`
- `ops/systemd/bet-agent-compose.service`
- `ops/systemd/bet-agent-pipeline.service`
- `ops/systemd/bet-agent-pipeline.timer`

## Preparacao da VPS

1. Instale Docker e Docker Compose.
2. Clone o repositorio em `/opt/bet-agent`.
3. Copie `bet_agent/.env.prd.example` para `bet_agent/.env.prd`.
4. Preencha as chaves reais.
5. Confirme que `DATA_DIR=/app/runtime` e `DIRETORIO_BANCO=/app/runtime`.

## Subida inicial

Na raiz do projeto:

```bash
docker compose up -d --build
```

Verificacoes:

```bash
docker compose ps
curl http://127.0.0.1:8000/health
```

## Pipeline manual

Para executar so a coleta:

```bash
docker compose run --rm --profile ops bet-agent-pipeline
```

## Nginx

Use `ops/nginx/bet-agent.conf.example` como base.

Depois:

```bash
sudo ln -s /opt/bet-agent/ops/nginx/bet-agent.conf.example /etc/nginx/sites-enabled/bet-agent.conf
sudo nginx -t
sudo systemctl reload nginx
```

## Agendamento diario

Copie os arquivos de `ops/systemd/` para `/etc/systemd/system/` e rode:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bet-agent-compose.service
sudo systemctl start bet-agent-compose.service
sudo systemctl enable bet-agent-pipeline.timer
sudo systemctl start bet-agent-pipeline.timer
```

## Persistencia

O `docker-compose.yml` usa o volume `bet_agent_runtime`.

Esse volume guarda:

- `cache_matches.json`
- historico por execucao
- banco SQLite `historico_apostas.db`

## Endpoints de verificacao

- `GET /health`
- `GET /bets`

## HTTPS

Depois que o dominio estiver apontado para a VPS:

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com
```

## Backup minimo recomendado

Salvar diariamente o volume de runtime ou exportar estes arquivos:

- `/app/runtime/cache_matches.json`
- `/app/runtime/history/`
- `/app/runtime/historico_apostas.db`
