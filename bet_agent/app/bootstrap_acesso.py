"""Inicializacao da base de acesso e do admin inicial."""

from __future__ import annotations

from app.config import settings
from db.repositorio_acesso import RepositorioAcessoSQLite
from services.autenticacao_service import AutenticacaoService


def inicializar_base_acesso() -> RepositorioAcessoSQLite:
    repositorio = RepositorioAcessoSQLite(settings.caminho_banco)
    AutenticacaoService.garantir_admin_inicial(
        repositorio,
        nome=settings.admin_nome_inicial,
        email=settings.admin_email_inicial,
        senha=settings.admin_senha_inicial,
    )
    return repositorio
