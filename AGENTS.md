# AGENTS.md

## Objetivo
Trabalhar com maxima eficiencia, com respostas curtas, e manter a documentacao do projeto sempre alinhada ao codigo.

## Estilo de resposta
- Responder de forma curta, direta e sem introducoes desnecessarias.
- Evitar explicar o obvio.
- Preferir 3 a 5 linhas no fechamento, salvo quando o trabalho exigir mais contexto.
- So usar listas quando elas realmente ajudarem.

## Modo de execucao
- Fazer primeiro e perguntar depois quando a duvida nao for bloqueante.
- Perguntar ao usuario apenas quando houver risco real, ambiguidade critica ou acao destrutiva.
- Ler apenas os arquivos necessarios para concluir a tarefa.
- Preferir a menor mudanca possivel no codigo.
- Nao refatorar fora do escopo sem necessidade clara.

## Regra permanente de documentacao
- Sempre que houver mudanca em codigo, configuracao, banco, API, pipeline, deploy, scripts ou fluxo operacional, revisar a documentacao afetada.
- Atualizar a documentacao no mesmo trabalho sempre que a mudanca alterar comportamento real do projeto.
- Se houver mudanca no schema, persistencia ou consultas, atualizar `bet_agent/docs/BANCO_DE_DADOS.md`.
- Se houver mudanca em comandos locais ou `.bat`, atualizar `bet_agent/docs/OPERACAO_LOCAL.md` e os READMEs quando necessario.
- Se houver mudanca em Docker, CI, GitHub ou VPS, atualizar a documentacao operacional correspondente.
- Ao concluir tarefas com alteracoes relevantes, informar claramente se a documentacao foi atualizada.

## Prioridades
- Menor diff util.
- Menor custo de tokens.
- Menor numero de idas e voltas.
- Validacao objetiva do que foi alterado.
- Documentacao consistente com o estado atual do projeto.

## Formato padrao de entrega
Ao concluir uma tarefa, responder com:
1. O que mudou.
2. Como foi validado.
3. Risco pendente, se existir.

## Quando revisar sem editar
Se o usuario pedir revisao, priorizar:
- bugs
- regressao
- risco
- testes faltando
- lacunas de documentacao, se houver

## Preferencias implicitas
- "so faca" = executar sem plano longo.
- "resposta curta" = resposta minima util.
- "menor diff possivel" = evitar reorganizacao e refatoracao.
- Assumir o caminho mais razoavel quando isso economizar tempo e tokens.
