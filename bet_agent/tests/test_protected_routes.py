import sqlite3
from types import SimpleNamespace
from urllib.parse import urlencode

from fastapi.testclient import TestClient

import app.bootstrap_acesso as bootstrap_module
import web.auth_routes as auth_routes_module
import web.dependencies as dependencies_module
import web.server as server_module
from db.repositorio_acesso import DadosNovoUsuario, RepositorioAcessoSQLite
from services.autenticacao_service import AutenticacaoService


def _auth_settings(db_path):
    return SimpleNamespace(
        caminho_banco=db_path,
        admin_nome_inicial="Admin",
        admin_email_inicial="tiagoch25@gmail.com",
        admin_senha_inicial="admin123",
        auth_cookie_name="oddsedge_auth",
        auth_session_duration_hours=168,
        auth_cookie_secure=False,
    )


def _build_client(monkeypatch, tmp_path):
    settings = _auth_settings(tmp_path / "historico_apostas.db")
    monkeypatch.setattr(bootstrap_module, "settings", settings)
    monkeypatch.setattr(auth_routes_module, "settings", settings)
    monkeypatch.setattr(dependencies_module, "settings", settings)
    monkeypatch.setattr(
        server_module,
        "settings",
        SimpleNamespace(
            app_env="test",
            data_file=tmp_path / "cache_matches.json",
            health_api_cache_seconds=300,
            use_sample_data=True,
        ),
    )
    client = TestClient(server_module.app)
    return client, settings


def _criar_usuario_base(db_path, *, nome, email, senha, perfil="usuario", plano="gratis", status="ativo"):
    repositorio = RepositorioAcessoSQLite(db_path)
    return repositorio.criar_usuario(
        DadosNovoUsuario(
            nome=nome,
            email=email,
            email_normalizado=AutenticacaoService.normalizar_email(email),
            senha_hash=AutenticacaoService.gerar_hash_senha(senha),
            perfil=perfil,
            plano=plano,
            status=status,
            expira_em=None,
        )
    )


def _login(client: TestClient, *, email: str, senha: str) -> None:
    response = client.post(
        "/auth/login",
        content=urlencode({"email": email, "senha": senha}),
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_dashboard_redirects_without_login(monkeypatch, tmp_path):
    client, _settings = _build_client(monkeypatch, tmp_path)

    with client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_dashboard_allows_logged_user(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Tiago", email="tiago@example.com", senha="segredo123")
        _login(client, email="tiago@example.com", senha="segredo123")
        response = client.get("/")

    assert response.status_code == 200
    assert "Tiago" in response.text
    assert "Sair" in response.text


def test_admin_blocks_common_user(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Tiago", email="tiago@example.com", senha="segredo123")
        _login(client, email="tiago@example.com", senha="segredo123")
        response = client.get("/admin", follow_redirects=False)

    assert response.status_code == 403


def test_admin_allows_admin_user(monkeypatch, tmp_path):
    client, _settings = _build_client(monkeypatch, tmp_path)

    with client:
        _login(client, email="tiagoch25@gmail.com", senha="admin123")
        response = client.get("/admin")

    assert response.status_code == 200
    assert "Painel administrativo inicial" in response.text


def test_admin_can_change_user_plan(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        usuario_id = _criar_usuario_base(
            settings.caminho_banco,
            nome="Tiago",
            email="tiago@example.com",
            senha="segredo123",
        )
        _login(client, email="tiagoch25@gmail.com", senha="admin123")
        response = client.post(
            f"/admin/usuarios/{usuario_id}/plano",
            content=urlencode({"plano": "pro"}),
            headers={"content-type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    with sqlite3.connect(settings.caminho_banco) as connection:
        plano = connection.execute(
            "SELECT plano FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()[0]

    assert plano == "pro"


def test_admin_can_block_user(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        usuario_id = _criar_usuario_base(
            settings.caminho_banco,
            nome="Tiago",
            email="tiago@example.com",
            senha="segredo123",
        )
        _login(client, email="tiagoch25@gmail.com", senha="admin123")
        response = client.post(
            f"/admin/usuarios/{usuario_id}/status",
            content=urlencode({"status": "bloqueado"}),
            headers={"content-type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    with sqlite3.connect(settings.caminho_banco) as connection:
        status = connection.execute(
            "SELECT status FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()[0]

    assert status == "bloqueado"


def test_blocked_user_loses_dashboard_access(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        usuario_id = _criar_usuario_base(
            settings.caminho_banco,
            nome="Tiago",
            email="tiago@example.com",
            senha="segredo123",
        )
        _login(client, email="tiago@example.com", senha="segredo123")
        RepositorioAcessoSQLite(settings.caminho_banco).atualizar_status_usuario(usuario_id, "bloqueado")
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
