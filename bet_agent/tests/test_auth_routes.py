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


def _criar_usuario_base(db_path, *, nome, email, senha, status="ativo"):
    repositorio = RepositorioAcessoSQLite(db_path)
    repositorio.criar_usuario(
        DadosNovoUsuario(
            nome=nome,
            email=email,
            email_normalizado=AutenticacaoService.normalizar_email(email),
            senha_hash=AutenticacaoService.gerar_hash_senha(senha),
            perfil="usuario",
            plano="gratis",
            status=status,
            expira_em=None,
        )
    )


def test_signup_valid_user(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        response = client.post(
            "/auth/cadastro",
            content=urlencode(
                {
                    "nome": "Tiago",
                    "email": "tiago@example.com",
                    "senha": "segredo123",
                    "confirmar_senha": "segredo123",
                }
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")

    with sqlite3.connect(settings.caminho_banco) as connection:
        row = connection.execute(
            """
            SELECT nome, email, perfil, plano, status
            FROM usuarios
            WHERE email_normalizado = 'tiago@example.com'
            """
        ).fetchone()

    assert row == ("Tiago", "tiago@example.com", "usuario", "gratis", "ativo")


def test_signup_blocks_duplicate_email(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Tiago", email="tiago@example.com", senha="segredo123")
        response = client.post(
            "/auth/cadastro",
            content=urlencode(
                {
                    "nome": "Outro",
                    "email": "Tiago@Example.com",
                    "senha": "segredo123",
                    "confirmar_senha": "segredo123",
                }
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 400
    assert "Este email ja esta cadastrado." in response.text


def test_signup_blocks_password_mismatch(monkeypatch, tmp_path):
    client, _settings = _build_client(monkeypatch, tmp_path)

    with client:
        response = client.post(
            "/auth/cadastro",
            content=urlencode(
                {
                    "nome": "Tiago",
                    "email": "tiago@example.com",
                    "senha": "segredo123",
                    "confirmar_senha": "senha-diferente",
                }
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 400
    assert "A confirmacao de senha nao confere." in response.text


def test_signup_blocks_invalid_email(monkeypatch, tmp_path):
    client, _settings = _build_client(monkeypatch, tmp_path)

    with client:
        response = client.post(
            "/auth/cadastro",
            content=urlencode(
                {
                    "nome": "Tiago",
                    "email": "tiago@dominio",
                    "senha": "segredo123",
                    "confirmar_senha": "segredo123",
                }
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 400
    assert "Informe um email valido." in response.text


def test_signup_blocks_weak_password(monkeypatch, tmp_path):
    client, _settings = _build_client(monkeypatch, tmp_path)

    with client:
        response = client.post(
            "/auth/cadastro",
            content=urlencode(
                {
                    "nome": "Tiago",
                    "email": "tiago@example.com",
                    "senha": "1234567",
                    "confirmar_senha": "1234567",
                }
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 400
    assert "Use pelo menos 10 caracteres" in response.text


def test_signup_blocks_password_based_on_name(monkeypatch, tmp_path):
    client, _settings = _build_client(monkeypatch, tmp_path)

    with client:
        response = client.post(
            "/auth/cadastro",
            content=urlencode(
                {
                    "nome": "Nome",
                    "email": "nome@example.com",
                    "senha": "Nome123456",
                    "confirmar_senha": "Nome123456",
                }
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 400
    assert "Use pelo menos 10 caracteres" in response.text


def test_login_with_valid_credentials(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Tiago", email="tiago@example.com", senha="segredo123")
        response = client.post(
            "/auth/login",
            content=urlencode({"email": "tiago@example.com", "senha": "segredo123"}),
            headers={"content-type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert settings.auth_cookie_name in response.headers.get("set-cookie", "")

    with sqlite3.connect(settings.caminho_banco) as connection:
        sessao = connection.execute(
            "SELECT COUNT(*) FROM sessoes_usuario WHERE ativo = 1"
        ).fetchone()[0]
        ultimo_login = connection.execute(
            "SELECT ultimo_login_em FROM usuarios WHERE email_normalizado = 'tiago@example.com'"
        ).fetchone()[0]

    assert sessao == 1
    assert ultimo_login is not None


def test_login_blocks_invalid_password(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Tiago", email="tiago@example.com", senha="segredo123")
        response = client.post(
            "/auth/login",
            content=urlencode({"email": "tiago@example.com", "senha": "errada"}),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 400
    assert "Senha invalida." in response.text


def test_login_blocks_unknown_user(monkeypatch, tmp_path):
    client, _settings = _build_client(monkeypatch, tmp_path)

    with client:
        response = client.post(
            "/auth/login",
            content=urlencode({"email": "naoexiste@example.com", "senha": "segredo123"}),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 400
    assert "Usuario nao encontrado." in response.text


def test_login_blocks_blocked_user(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        _criar_usuario_base(
            settings.caminho_banco,
            nome="Tiago",
            email="tiago@example.com",
            senha="segredo123",
            status="bloqueado",
        )
        response = client.post(
            "/auth/login",
            content=urlencode({"email": "tiago@example.com", "senha": "segredo123"}),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 400
    assert "Seu usuario esta bloqueado." in response.text


def test_login_creates_session_record(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Tiago", email="tiago@example.com", senha="segredo123")
        client.post(
            "/auth/login",
            content=urlencode({"email": "tiago@example.com", "senha": "segredo123"}),
            headers={"content-type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )

    with sqlite3.connect(settings.caminho_banco) as connection:
        row = connection.execute(
            """
            SELECT usuario_id, token_sessao_hash, ativo, ip, user_agent
            FROM sessoes_usuario
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert row is not None
    assert row[0] is not None
    assert row[1]
    assert row[2] == 1


def test_logout_invalidates_current_session(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Tiago", email="tiago@example.com", senha="segredo123")
        client.post(
            "/auth/login",
            content=urlencode({"email": "tiago@example.com", "senha": "segredo123"}),
            headers={"content-type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        response = client.post("/auth/logout", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
    assert "Max-Age=0" in response.headers.get("set-cookie", "")

    with sqlite3.connect(settings.caminho_banco) as connection:
        row = connection.execute(
            """
            SELECT ativo, encerrada_em
            FROM sessoes_usuario
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert row is not None
    assert row[0] == 0
    assert row[1] is not None


def test_password_strength_analysis_levels():
    fraca = AutenticacaoService.analisar_forca_senha("1234567")
    fraca_nome = AutenticacaoService.analisar_forca_senha("Nome123456", nome="Nome", email="nome@example.com")
    normal = AutenticacaoService.analisar_forca_senha("segredo123")
    forte = AutenticacaoService.analisar_forca_senha("SenhaMuitoBoa123!")

    assert fraca.nivel == "fraca"
    assert fraca_nome.nivel == "fraca"
    assert normal.nivel == "normal"
    assert forte.nivel == "forte"
