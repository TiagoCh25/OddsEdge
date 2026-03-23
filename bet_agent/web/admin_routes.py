"""Rotas protegidas da area admin inicial."""

from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.autenticacao_service import AutenticacaoErro, AutenticacaoService
from web.dependencies import exigir_admin, get_repositorio_acesso, redirecionar_para_login

router = APIRouter()

base_dir = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(base_dir / "web" / "templates"))


async def _parse_form_urlencoded(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _redirect_admin(**params: str) -> RedirectResponse:
    filtros = {key: value for key, value in params.items() if str(value or "").strip()}
    url = "/admin"
    if filtros:
        url = f"{url}?{urlencode(filtros)}"
    return RedirectResponse(url=url, status_code=303)


def _render_admin(
    request: Request,
    *,
    usuario_atual: dict[str, object],
    mensagem_erro: str = "",
    mensagem_sucesso: str = "",
) -> HTMLResponse:
    repositorio = get_repositorio_acesso()
    response = templates.TemplateResponse(
        request,
        "admin.html",
        {
            "request": request,
            "static_version": str(int(time.time())),
            "usuario_atual": usuario_atual,
            "mensagem_erro": mensagem_erro,
            "mensagem_sucesso": mensagem_sucesso,
            "resumo": repositorio.obter_resumo_usuarios(),
            "usuarios": repositorio.listar_usuarios(),
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    try:
        usuario_atual = exigir_admin(request)
    except HTTPException as exc:
        if exc.status_code == 401:
            return redirecionar_para_login(str(exc.detail))
        raise

    return _render_admin(
        request,
        usuario_atual=usuario_atual,
        mensagem_erro=str(request.query_params.get("erro", "") or ""),
        mensagem_sucesso=str(request.query_params.get("sucesso", "") or ""),
    )


@router.post("/admin/usuarios/{usuario_id}/plano")
async def admin_atualizar_plano(usuario_id: int, request: Request):
    try:
        exigir_admin(request)
    except HTTPException as exc:
        if exc.status_code == 401:
            return redirecionar_para_login(str(exc.detail))
        raise

    form = await _parse_form_urlencoded(request)
    plano = str(form.get("plano", "") or "")
    repositorio = get_repositorio_acesso()

    try:
        linhas = AutenticacaoService.atualizar_plano_usuario(
            repositorio,
            usuario_id=usuario_id,
            plano=plano,
        )
    except AutenticacaoErro as exc:
        return _redirect_admin(erro=str(exc))

    if not linhas:
        return _redirect_admin(erro="Usuario nao encontrado para atualizar o plano.")
    return _redirect_admin(sucesso="Plano atualizado com sucesso.")


@router.post("/admin/usuarios/{usuario_id}/status")
async def admin_atualizar_status(usuario_id: int, request: Request):
    try:
        exigir_admin(request)
    except HTTPException as exc:
        if exc.status_code == 401:
            return redirecionar_para_login(str(exc.detail))
        raise

    form = await _parse_form_urlencoded(request)
    status = str(form.get("status", "") or "")
    repositorio = get_repositorio_acesso()

    try:
        linhas = AutenticacaoService.atualizar_status_usuario(
            repositorio,
            usuario_id=usuario_id,
            status=status,
        )
    except AutenticacaoErro as exc:
        return _redirect_admin(erro=str(exc))

    if not linhas:
        return _redirect_admin(erro="Usuario nao encontrado para atualizar o status.")
    return _redirect_admin(sucesso="Status atualizado com sucesso.")
