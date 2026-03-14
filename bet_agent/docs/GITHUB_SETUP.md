# Setup GitHub

## Objetivo

Deixar o projeto versionado de forma profissional e pronto para usar CI/CD no GitHub.

## O que ja ficou preparado no repositorio

- `.gitignore`
- `README.md` na raiz
- workflows em `.github/workflows/`
- template de Pull Request

## Passo a passo

1. Crie uma conta no GitHub, de preferencia com perfil profissional.
2. Crie um repositorio novo, por exemplo `bet-agent`.
3. No computador, entre na pasta raiz `Dicas_BET`.
4. Inicialize o repositorio local, se ainda nao existir:

```bash
git init -b main
```

5. Adicione os arquivos:

```bash
git add .
git commit -m "chore: bootstrap professional project structure"
```

6. Conecte o remoto:

```bash
git remote add origin https://github.com/SEU_USUARIO/bet-agent.git
git push -u origin main
```

## Configuracoes recomendadas no GitHub

- ativar branch protection na `main`
- exigir pull request para merge
- exigir workflow `ci` verde antes do merge
- habilitar GitHub Packages se quiser publicar imagem Docker no GHCR

## Segredos recomendados

Para deploy futuro, configure no GitHub ou no servidor:

- `API_FOOTBALL_KEY`
- `THE_ODDS_API_KEY`

## Quando vale criar uma conta profissional

Crie ou organize o perfil profissional se voce quiser:

- portfolio publico de projetos
- historico limpo separado de testes pessoais
- usar dominio/organizacao no futuro

Se voce ainda nao tiver conta profissional, esse e o unico ponto externo que eu nao consigo fazer daqui. Quando quiser, eu posso te passar o passo a passo exato da interface do GitHub tambem.
