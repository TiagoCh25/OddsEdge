"""Dependencias e helpers leves para autenticacao baseada em sessao."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import settings
from db.repositorio_acesso import RepositorioAcessoSQLite
from services.autenticacao_service import AutenticacaoService


def get_repositorio_acesso() -> RepositorioAcessoSQLite:
    return RepositorioAcessoSQLite(settings.caminho_banco)


def obter_usuario_logado(request: Request) -> dict[str, Any] | None:
    token_sessao = request.cookies.get(settings.auth_cookie_name, "")
    if not token_sessao:
        return None
    return AutenticacaoService.obter_usuario_por_token_sessao(
        get_repositorio_acesso(),
        token_sessao,
    )


def exigir_usuario_logado(request: Request) -> dict[str, Any]:
    usuario = obter_usuario_logado(request)
    if not usuario:
        raise HTTPException(status_code=401, detail="Sua sessao expirou. Entre novamente.")
    return usuario


def exigir_admin(request: Request) -> dict[str, Any]:
    usuario = exigir_usuario_logado(request)
    if str(usuario.get("perfil") or "") != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return usuario


def redirecionar_para_login(mensagem: str = "") -> RedirectResponse:
    url = "/login"
    mensagem_limpa = str(mensagem or "").strip()
    if mensagem_limpa:
        url = f"{url}?{urlencode({'erro': mensagem_limpa})}"
    return RedirectResponse(url=url, status_code=303)


def obter_usuario_logado_opcional(request: Request) -> dict[str, Any] | None:
    return obter_usuario_logado(request)
