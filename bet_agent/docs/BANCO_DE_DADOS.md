# Banco de Dados

## Visao geral

O projeto usa SQLite para historico operacional e para a base inicial de acesso.

O arquivo do banco e definido por:

- `DIRETORIO_BANCO`
- `NOME_ARQUIVO_BANCO`

Se `DIRETORIO_BANCO` nao for definido, o projeto usa `DATA_DIR` ou o diretorio padrao de runtime.

## Tabelas

### `execucoes`

Representa uma execucao completa do pipeline.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | INTEGER | PK autoincremento |
| `execucao_id` | TEXT | identificador unico da execucao |
| `gerado_em` | TEXT | timestamp do payload |
| `data_referencia` | TEXT | data do processamento |
| `ambiente` | TEXT | `local`, `prd` etc. |
| `fonte_dados` | TEXT | `live` ou `sample` |
| `status_execucao` | TEXT | status geral |
| `mensagem_erro` | TEXT | erro global, se houver |
| `total_jogos_analisados` | INTEGER | quantidade total de jogos |
| `total_jogos_com_odds` | INTEGER | jogos com odds encontradas |
| `total_apostas` | INTEGER | total de apostas recomendadas |
| `odd_combinada_top2` | REAL | combinacao das 2 melhores odds |
| `payload_json` | TEXT | snapshot completo do payload |
| `criado_em` | TEXT | timestamp de persistencia |

Restricao:

- `execucao_id` e unico

### `partidas`

Armazena os jogos processados por execucao.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | INTEGER | PK autoincremento |
| `execucao_id` | TEXT | referencia logica da execucao |
| `fixture_id` | INTEGER | id do jogo na API |
| `chave_partida` | TEXT | chave normalizada do confronto |
| `kickoff` | TEXT | data/hora do jogo |
| `liga_id` | INTEGER | id da liga |
| `liga_nome` | TEXT | nome da liga |
| `liga_logo` | TEXT | logo da liga |
| `pais` | TEXT | pais da liga |
| `temporada` | INTEGER | temporada |
| `time_casa_id` | INTEGER | id do time da casa |
| `time_casa_nome` | TEXT | nome do time da casa |
| `time_casa_logo` | TEXT | logo do time da casa |
| `time_fora_id` | INTEGER | id do time visitante |
| `time_fora_nome` | TEXT | nome do time visitante |
| `time_fora_logo` | TEXT | logo do time visitante |
| `status_curto` | TEXT | status resumido do jogo |
| `status_jogo` | TEXT | status completo do jogo |
| `gols_casa` | INTEGER | gols da casa |
| `gols_fora` | INTEGER | gols do visitante |
| `stats_basis_json` | TEXT | base estatistica usada no calculo |
| `criado_em` | TEXT | timestamp de persistencia |

Restricao:

- `UNIQUE(execucao_id, fixture_id)`

### `odds_partidas`

Armazena odds por mercado e partida.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | INTEGER | PK autoincremento |
| `execucao_id` | TEXT | referencia logica da execucao |
| `fixture_id` | INTEGER | id do jogo |
| `chave_partida` | TEXT | chave normalizada |
| `mercado_chave` | TEXT | identificador do mercado |
| `odd` | REAL | valor decimal da odd |
| `criado_em` | TEXT | timestamp de persistencia |

Restricao:

- `UNIQUE(execucao_id, fixture_id, mercado_chave)`

### `apostas_recomendadas`

Armazena cada recomendacao gerada.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | INTEGER | PK autoincremento |
| `execucao_id` | TEXT | referencia logica da execucao |
| `fixture_id` | INTEGER | id do jogo |
| `jogo` | TEXT | confronto em texto |
| `liga` | TEXT | nome da liga |
| `liga_logo` | TEXT | logo da liga |
| `time_casa` | TEXT | time da casa |
| `time_fora` | TEXT | time visitante |
| `logo_time_casa` | TEXT | logo da casa |
| `logo_time_fora` | TEXT | logo do visitante |
| `tipo_aposta` | TEXT | nome amigavel do mercado |
| `mercado_chave` | TEXT | chave tecnica do mercado |
| `probabilidade` | REAL | probabilidade em decimal |
| `probabilidade_percentual` | REAL | probabilidade em percentual |
| `odd` | REAL | odd decimal |
| `ev` | REAL | expected value |
| `kickoff` | TEXT | data/hora do jogo |
| `status_curto` | TEXT | status resumido |
| `status_jogo` | TEXT | status detalhado |
| `gols_casa` | INTEGER | gols da casa |
| `gols_fora` | INTEGER | gols do visitante |
| `stats_basis_json` | TEXT | base estatistica usada |
| `resultado_aposta` | TEXT | `pendente`, `ganhou`, `perdeu`, `indefinido` |
| `placar_final` | TEXT | placar final em texto |
| `criado_em` | TEXT | timestamp de persistencia |

Restricao:

- `UNIQUE(execucao_id, fixture_id, tipo_aposta)`

### `erros_processamento`

Armazena erros por partida sem derrubar a execucao inteira.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | INTEGER | PK autoincremento |
| `execucao_id` | TEXT | referencia logica da execucao |
| `fixture_id` | INTEGER | id do jogo, quando conhecido |
| `jogo` | TEXT | confronto em texto |
| `liga` | TEXT | nome da liga |
| `time_nome` | TEXT | time associado ao erro, quando identificado |
| `time_id` | INTEGER | id do time associado ao erro |
| `lado_time` | TEXT | `home` ou `away`, quando conhecido |
| `etapa` | TEXT | etapa do pipeline em que o erro ocorreu |
| `mensagem_erro` | TEXT | mensagem amigavel do erro |
| `detalhe_json` | TEXT | snapshot completo do erro persistido |
| `criado_em` | TEXT | timestamp de persistencia |

### `usuarios`

Base inicial de usuarios do MVP comercial.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | INTEGER | PK autoincremento |
| `nome` | TEXT | nome do usuario |
| `email` | TEXT | email original informado |
| `email_normalizado` | TEXT | email normalizado para busca e unicidade |
| `senha_hash` | TEXT | hash seguro da senha |
| `perfil` | TEXT | `usuario` ou `admin` |
| `plano` | TEXT | `gratis` ou `pro` |
| `status` | TEXT | `ativo` ou `bloqueado` |
| `criado_em` | TEXT | timestamp de criacao |
| `atualizado_em` | TEXT | timestamp de ultima atualizacao |
| `ultimo_login_em` | TEXT | timestamp do ultimo login, quando existir |
| `expira_em` | TEXT | expiracao do acesso, quando aplicavel |

Regras:

- `email` e unico
- `email_normalizado` e unico
- indices auxiliares em `perfil`, `plano` e `status`

### `planos`

Catalogo inicial de planos do produto.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | INTEGER | PK autoincremento |
| `codigo` | TEXT | identificador unico do plano |
| `nome` | TEXT | nome exibido |
| `descricao` | TEXT | descricao curta |
| `limite_apostas_dia` | INTEGER | limite diario; `NULL` quando nao houver |
| `preco_mensal_centavos` | INTEGER | preco mensal em centavos |
| `ativo` | INTEGER | `1` ativo, `0` inativo |
| `criado_em` | TEXT | timestamp de criacao |
| `atualizado_em` | TEXT | timestamp de ultima atualizacao |

Seeds idempotentes:

- `gratis`: `Grátis`, `1 recomendação por dia`, limite `1`, preco `0`, ativo `1`
- `pro`: `Pro`, `acesso completo às recomendações`, limite `NULL`, preco `0`, ativo `1`

### `sessoes_usuario`

Estrutura de autenticacao via sessao para login e logout do MVP.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | INTEGER | PK autoincremento |
| `usuario_id` | INTEGER | FK para `usuarios.id` |
| `token_sessao_hash` | TEXT | hash unico do token da sessao |
| `criado_em` | TEXT | timestamp de criacao |
| `atualizado_em` | TEXT | timestamp de atualizacao |
| `expira_em` | TEXT | expiracao da sessao |
| `encerrada_em` | TEXT | encerramento explicito, quando existir |
| `ativo` | INTEGER | `1` ativa, `0` inativa |
| `ip` | TEXT | IP de origem, quando disponivel |
| `user_agent` | TEXT | user-agent da sessao, quando disponivel |

Regras:

- `usuario_id` referencia `usuarios(id)`
- indice por `usuario_id`
- indice unico por `token_sessao_hash`
- indice por `expira_em` e `ativo`
- o cookie do navegador guarda apenas o token real; o banco persiste somente `token_sessao_hash`
- quando um usuario e bloqueado pela area admin, suas sessoes ativas sao invalidadas

## Bootstrap inicial

Ao subir a camada web, o projeto inicializa de forma idempotente:

- as tabelas `usuarios`, `planos` e `sessoes_usuario`
- os planos `gratis` e `pro`
- um usuario admin inicial, se ainda nao existir nenhum `perfil='admin'`

## Mercados suportados

- `over_0_5`
- `over_1_5`
- `over_2_5`
- `over_3_5`
- `under_2_5`
- `under_3_5`
- `btts_yes`
- `btts_no`
- `home_win`
- `draw`
- `away_win`
- `double_chance_1x`
- `double_chance_x2`
- `double_chance_12`

## Como consultar

### Ferramenta visual

Voce pode abrir o arquivo `.db` em:

- DBeaver
- DB Browser for SQLite

### Exemplo com `sqlite3`

```bash
sqlite3 historico_apostas.db
```

```sql
.tables
SELECT * FROM execucoes ORDER BY id DESC LIMIT 5;
SELECT jogo, tipo_aposta, odd, ev FROM apostas_recomendadas ORDER BY id DESC LIMIT 20;
```

## Queries uteis

### Ultimas execucoes

```sql
SELECT id, execucao_id, data_referencia, status_execucao, total_apostas
FROM execucoes
ORDER BY id DESC
LIMIT 10;
```

### Apostas mais recentes

```sql
SELECT jogo, liga, tipo_aposta, probabilidade_percentual, odd, ev, resultado_aposta
FROM apostas_recomendadas
ORDER BY id DESC
LIMIT 20;
```

### Quantidade por liga

```sql
SELECT liga, COUNT(*) AS total
FROM apostas_recomendadas
GROUP BY liga
ORDER BY total DESC;
```

### Taxa de acerto encerrada

```sql
SELECT
  resultado_aposta,
  COUNT(*) AS total
FROM apostas_recomendadas
WHERE resultado_aposta IN ('ganhou', 'perdeu')
GROUP BY resultado_aposta;
```

### Erros mais recentes por partida

```sql
SELECT jogo, liga, time_nome, etapa, mensagem_erro, criado_em
FROM erros_processamento
ORDER BY id DESC
LIMIT 20;
```
