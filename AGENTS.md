# AGENTS.md

## Objetivo
Trabalhar com maximo de eficiencia e minimo de tokens.

## Estilo de resposta
- Responder de forma curta, direta e sem introducoes.
- Evitar explicar o obvio.
- Preferir 3 a 5 linhas no fechamento.
- So usar listas quando realmente ajudar.

## Modo de execucao
- Fazer primeiro e perguntar depois quando a duvida nao for bloqueante.
- Perguntar ao usuario apenas quando houver risco real, ambiguidade critica ou acao destrutiva.
- Ler apenas os arquivos necessarios para concluir a tarefa.
- Preferir a menor mudanca possivel no codigo.
- Nao refatorar fora do escopo sem necessidade clara.

## Prioridades
- Menor diff util.
- Menor custo de tokens.
- Menor numero de idas e voltas.
- Validacao objetiva do que foi alterado.

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

## Preferencias implicitas
- "só faça" = executar sem plano longo.
- "resposta curta" = resposta minima util.
- "menor diff possivel" = evitar reorganizacao e refatoracao.
- Assumir o caminho mais razoavel quando isso economizar tempo e tokens.
