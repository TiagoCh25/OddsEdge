"""Rotas HTML e POSTs para login, cadastro e logout."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from services.autenticacao_service import (
    AutenticacaoErro,
    AutenticacaoService,
    ResultadoSessaoAutenticada,
)
from web.dependencies import get_repositorio_acesso, obter_usuario_logado_opcional

router = APIRouter()

base_dir = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(base_dir / "web" / "templates"))


def _redirect_with_message(path: str, **params: str) -> RedirectResponse:
    filtered = {key: value for key, value in params.items() if str(value or "").strip()}
    if filtered:
        path = f"{path}?{urlencode(filtered)}"
    return RedirectResponse(url=path, status_code=303)


def _render_auth_template(
    template_name: str,
    request: Request,
    *,
    titulo: str,
    subtitulo: str,
    acao: str,
    mensagem_erro: str = "",
    mensagem_sucesso: str = "",
    valores: dict[str, str] | None = None,
    extra_context: dict[str, object] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    context = {
        "request": request,
        "titulo": titulo,
        "subtitulo": subtitulo,
        "acao": acao,
        "mensagem_erro": mensagem_erro,
        "mensagem_sucesso": mensagem_sucesso,
        "valores": valores or {},
        "static_version": str(int(time.time())),
    }
    if extra_context:
        context.update(extra_context)
    response = templates.TemplateResponse(
        request,
        template_name,
        context,
    )
    response.status_code = status_code
    response.headers["Cache-Control"] = "no-store"
    return response


async def _parse_form_urlencoded(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _request_ip(request: Request) -> str:
    client = getattr(request, "client", None)
    return str(client.host) if client and getattr(client, "host", None) else ""


def _request_user_agent(request: Request) -> str:
    return str(request.headers.get("user-agent", "") or "")


def _set_auth_cookie(response: RedirectResponse, sessao: ResultadoSessaoAutenticada) -> None:
    max_age = max(int((sessao.expira_em - datetime.now()).total_seconds()), 1)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=sessao.token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=max_age,
        expires=max_age,
        path="/",
    )


def _clear_auth_cookie(response: RedirectResponse) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if obter_usuario_logado_opcional(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return _render_auth_template(
        "login.html",
        request,
        titulo="Entrar",
        subtitulo="Acesse sua conta para continuar no OddsEdge.",
        acao="/auth/login",
        mensagem_erro=str(request.query_params.get("erro", "") or ""),
        mensagem_sucesso=str(request.query_params.get("sucesso", "") or ""),
    )


@router.get("/cadastro", response_class=HTMLResponse)
def cadastro_page(request: Request):
    if obter_usuario_logado_opcional(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return _render_auth_template(
        "cadastro.html",
        request,
        titulo="Criar conta",
        subtitulo="Comece com acesso gratis e evolua depois.",
        acao="/auth/cadastro",
        mensagem_erro=str(request.query_params.get("erro", "") or ""),
        mensagem_sucesso=str(request.query_params.get("sucesso", "") or ""),
    )


@router.get("/esqueci-senha", response_class=HTMLResponse)
def esqueci_senha_page(request: Request):
    if obter_usuario_logado_opcional(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return _render_auth_template(
        "esqueci_senha.html",
        request,
        titulo="Recuperar senha",
        subtitulo="Informe seu email e enviaremos um link para redefinicao de senha.",
        acao="/auth/esqueci-senha",
        mensagem_erro=str(request.query_params.get("erro", "") or ""),
        mensagem_sucesso=str(request.query_params.get("sucesso", "") or ""),
    )


@router.get("/redefinir-senha", response_class=HTMLResponse)
def redefinir_senha_page(request: Request):
    if obter_usuario_logado_opcional(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    token = str(request.query_params.get("token", "") or "")
    mensagem_erro = str(request.query_params.get("erro", "") or "")
    token_valido = False
    if token and not mensagem_erro:
        try:
            AutenticacaoService.validar_token_recuperacao(get_repositorio_acesso(), token)
            token_valido = True
        except AutenticacaoErro as exc:
            mensagem_erro = str(exc)
    return _render_auth_template(
        "redefinir_senha.html",
        request,
        titulo="Redefinir senha",
        subtitulo="Defina uma nova senha para voltar a acessar sua conta.",
        acao="/auth/redefinir-senha",
        mensagem_erro=mensagem_erro,
        mensagem_sucesso=str(request.query_params.get("sucesso", "") or ""),
        extra_context={"token": token, "token_valido": token_valido},
        status_code=400 if mensagem_erro else 200,
    )


@router.post("/auth/cadastro")
async def auth_cadastro(request: Request):
    if obter_usuario_logado_opcional(request):
        return RedirectResponse(url="/dashboard", status_code=303)

    form = await _parse_form_urlencoded(request)
    nome = str(form.get("nome", "") or "")
    email = str(form.get("email", "") or "")
    senha = str(form.get("senha", "") or "")
    confirmar_senha = str(form.get("confirmar_senha", "") or "")
    repositorio = get_repositorio_acesso()

    try:
        AutenticacaoService.cadastrar_usuario(
            repositorio,
            nome=nome,
            email=email,
            senha=senha,
            confirmar_senha=confirmar_senha,
        )
    except AutenticacaoErro as exc:
        return _render_auth_template(
            "cadastro.html",
            request,
            titulo="Criar conta",
            subtitulo="Comece com acesso gratis e evolua depois.",
            acao="/auth/cadastro",
            mensagem_erro=str(exc),
            valores={"nome": nome, "email": email},
            status_code=400,
        )

    return _redirect_with_message("/login", sucesso="Cadastro realizado com sucesso. Entre para continuar.")


@router.post("/auth/login")
async def auth_login(request: Request):
    if obter_usuario_logado_opcional(request):
        return RedirectResponse(url="/dashboard", status_code=303)

    form = await _parse_form_urlencoded(request)
    email = str(form.get("email", "") or "")
    senha = str(form.get("senha", "") or "")
    repositorio = get_repositorio_acesso()

    try:
        usuario = AutenticacaoService.autenticar_usuario(
            repositorio,
            email=email,
            senha=senha,
        )
    except AutenticacaoErro as exc:
        return _render_auth_template(
            "login.html",
            request,
            titulo="Entrar",
            subtitulo="Acesse sua conta para continuar no OddsEdge.",
            acao="/auth/login",
            mensagem_erro=str(exc),
            valores={"email": email},
            status_code=400,
        )

    sessao = AutenticacaoService.criar_sessao_autenticada(
        repositorio,
        usuario_id=int(usuario["id"]),
        duracao_horas=settings.auth_session_duration_hours,
        ip=_request_ip(request),
        user_agent=_request_user_agent(request),
    )
    response = RedirectResponse(url="/dashboard", status_code=303)
    _set_auth_cookie(response, sessao)
    return response


@router.post("/auth/esqueci-senha")
async def auth_esqueci_senha(request: Request):
    if obter_usuario_logado_opcional(request):
        return RedirectResponse(url="/dashboard", status_code=303)

    form = await _parse_form_urlencoded(request)
    email = str(form.get("email", "") or "")

    try:
        AutenticacaoService.solicitar_recuperacao_senha(
            get_repositorio_acesso(),
            email=email,
            duracao_minutos=settings.reset_senha_expiracao_minutos,
            app_base_url=settings.app_base_url,
            ip=_request_ip(request),
            user_agent=_request_user_agent(request),
        )
    except AutenticacaoErro as exc:
        return _render_auth_template(
            "esqueci_senha.html",
            request,
            titulo="Recuperar senha",
            subtitulo="Informe seu email e enviaremos um link para redefinicao de senha.",
            acao="/auth/esqueci-senha",
            mensagem_erro=str(exc),
            valores={"email": email},
            status_code=400,
        )

    return _redirect_with_message(
        "/esqueci-senha",
        sucesso="Se existir uma conta com esse email, enviaremos um link de recuperacao.",
    )


@router.post("/auth/redefinir-senha")
async def auth_redefinir_senha(request: Request):
    if obter_usuario_logado_opcional(request):
        return RedirectResponse(url="/dashboard", status_code=303)

    form = await _parse_form_urlencoded(request)
    token = str(form.get("token", "") or "")
    senha = str(form.get("senha", "") or "")
    confirmar_senha = str(form.get("confirmar_senha", "") or "")

    try:
        AutenticacaoService.redefinir_senha_por_token(
            get_repositorio_acesso(),
            token=token,
            senha=senha,
            confirmar_senha=confirmar_senha,
        )
    except AutenticacaoErro as exc:
        return _render_auth_template(
            "redefinir_senha.html",
            request,
            titulo="Redefinir senha",
            subtitulo="Defina uma nova senha para voltar a acessar sua conta.",
            acao="/auth/redefinir-senha",
            mensagem_erro=str(exc),
            extra_context={"token": token, "token_valido": True},
            status_code=400,
        )

    return _redirect_with_message("/login", sucesso="Senha redefinida com sucesso. Entre com a nova senha.")


@router.post("/auth/logout")
def auth_logout(request: Request):
    token_sessao = request.cookies.get(settings.auth_cookie_name, "")
    if token_sessao:
        AutenticacaoService.encerrar_sessao(get_repositorio_acesso(), token_sessao)

    response = _redirect_with_message("/login", sucesso="Logout realizado com sucesso.")
    _clear_auth_cookie(response)
    return response
