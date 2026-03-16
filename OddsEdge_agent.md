# OddsEdge_agent.md

## Escopo
Este agente vale apenas para o projeto `OddsEdge` deste repositorio.

## Missao
Manter o projeto com maxima eficiencia operacional e manter toda a documentacao alinhada com o estado real do codigo.

## Responsabilidade permanente
Este agente sera responsavel por revisar e atualizar toda e qualquer documentacao afetada sempre que houver mudancas relevantes no projeto, especialmente quando a branch `main` for atualizada.

## Quando atualizar documentacao
- mudanca em codigo
- mudanca em configuracao
- mudanca em banco de dados
- mudanca em schema, tabelas, colunas ou consultas
- mudanca em API ou endpoints
- mudanca em pipeline, CI ou automacao
- mudanca em Docker, deploy ou VPS
- mudanca em scripts `.bat` ou fluxo local
- mudanca em comandos, variaveis de ambiente ou operacao

## Regras obrigatorias
- atualizar a documentacao no mesmo trabalho em que a mudanca for feita
- nao deixar README, docs operacionais ou docs de banco desatualizados
- se houver mudanca no banco, atualizar `bet_agent/docs/BANCO_DE_DADOS.md`
- se houver mudanca em operacao local, atualizar `bet_agent/docs/OPERACAO_LOCAL.md`
- se houver mudanca em Docker, CI, GitHub ou VPS, atualizar os docs correspondentes
- se houver mudanca estrutural do projeto, revisar `bet_agent/README.md` e `bet_agent/docs/README.md`

## Prioridade
- documentacao consistente com a branch `main`
- menor diff util
- menor custo de tokens
- execucao direta com poucas perguntas

## Forma de resposta
Ao concluir tarefas relevantes, informar:
1. o que mudou
2. como foi validado
3. qual documentacao foi atualizada
4. risco pendente, se existir
