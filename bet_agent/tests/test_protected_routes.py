import json
import sqlite3
from datetime import datetime, timedelta
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


def _salvar_payload_dashboard(tmp_path, bets):
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scores_updated_at": None,
        "total_games_analyzed": len(bets),
        "total_bets": len(bets),
        "combined_odd_top2": None,
        "bets": bets,
        "data_source": "sample",
        "status": "ok",
        "error_message": None,
        "warning_message": None,
        "warning_details": None,
    }
    (tmp_path / "cache_matches.json").write_text(json.dumps(payload), encoding="utf-8")


def _bet_payload(*, fixture_id, probability, odd, kickoff, status_short="NS", status_jogo="Not Started"):
    return {
        "fixture_id": fixture_id,
        "jogo": f"Time {fixture_id} A vs Time {fixture_id} B",
        "liga": "Liga Teste",
        "tipo_aposta": "Over 1.5 gols",
        "probability": probability,
        "probabilidade": probability * 100,
        "odd": odd,
        "ev": 0.1,
        "kickoff": kickoff,
        "status_short": status_short,
        "status_jogo": status_jogo,
        "home_goals": None,
        "away_goals": None,
    }


def test_dashboard_redirects_without_login(monkeypatch, tmp_path):
    client, _settings = _build_client(monkeypatch, tmp_path)

    with client:
        response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_dashboard_allows_logged_user(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Tiago", email="tiago@example.com", senha="segredo123")
        _login(client, email="tiago@example.com", senha="segredo123")
        response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Tiago" in response.text
    assert "Sair" in response.text


def test_root_returns_landing_without_login(monkeypatch, tmp_path):
    client, _settings = _build_client(monkeypatch, tmp_path)

    with client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Mais dados. Menos achismo." in response.text
    assert 'href="/cadastro"' in response.text
    assert 'href="/login"' in response.text


def test_root_redirects_authenticated_user_to_dashboard(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Tiago", email="tiago@example.com", senha="segredo123")
        _login(client, email="tiago@example.com", senha="segredo123")
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


def test_landing_links_are_correct(monkeypatch, tmp_path):
    client, _settings = _build_client(monkeypatch, tmp_path)

    with client:
        response = client.get("/")

    assert response.status_code == 200
    assert 'href="/login"' in response.text
    assert 'href="/cadastro"' in response.text
    assert 'href="#como-funciona"' in response.text
    assert 'href="#beneficios"' in response.text
    assert 'href="#planos"' in response.text


def test_planos_route_renders_landing_even_when_authenticated(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Tiago", email="tiago@example.com", senha="segredo123")
        _login(client, email="tiago@example.com", senha="segredo123")
        response = client.get("/planos")

    assert response.status_code == 200
    assert "Plano Pro" in response.text
    assert "Como funciona o plano Gratis" in response.text


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
        response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_free_user_receives_only_one_eligible_recommendation(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)
    now = datetime.now()
    _salvar_payload_dashboard(
        tmp_path,
        [
            _bet_payload(
                fixture_id=1,
                probability=0.81,
                odd=1.45,
                kickoff=(now + timedelta(hours=3)).isoformat(timespec="seconds"),
            ),
            _bet_payload(
                fixture_id=2,
                probability=0.77,
                odd=1.70,
                kickoff=(now + timedelta(hours=4)).isoformat(timespec="seconds"),
            ),
        ],
    )

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Gratis", email="gratis@example.com", senha="segredo123")
        _login(client, email="gratis@example.com", senha="segredo123")
        response = client.get("/bets")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["bets"]) == 1
    assert payload["bets"][0]["fixture_id"] == 1
    assert payload["dashboard_estado"] == "gratis_com_recomendacao"


def test_pro_user_receives_all_valid_recommendations(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)
    now = datetime.now()
    _salvar_payload_dashboard(
        tmp_path,
        [
            _bet_payload(
                fixture_id=1,
                probability=0.81,
                odd=1.20,
                kickoff=(now + timedelta(minutes=40)).isoformat(timespec="seconds"),
            ),
            _bet_payload(
                fixture_id=2,
                probability=0.77,
                odd=1.70,
                kickoff=(now + timedelta(hours=4)).isoformat(timespec="seconds"),
            ),
            _bet_payload(
                fixture_id=3,
                probability=0.72,
                odd=1.55,
                kickoff=(now - timedelta(minutes=5)).isoformat(timespec="seconds"),
                status_short="1H",
                status_jogo="First Half",
            ),
        ],
    )

    with client:
        _criar_usuario_base(
            settings.caminho_banco,
            nome="Pro",
            email="pro@example.com",
            senha="segredo123",
            plano="pro",
        )
        _login(client, email="pro@example.com", senha="segredo123")
        response = client.get("/bets")

    assert response.status_code == 200
    payload = response.json()
    assert [bet["fixture_id"] for bet in payload["bets"]] == [1, 2, 3]
    assert payload["dashboard_estado"] == "completo"


def test_admin_receives_all_valid_recommendations(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)
    now = datetime.now()
    _salvar_payload_dashboard(
        tmp_path,
        [
            _bet_payload(
                fixture_id=10,
                probability=0.76,
                odd=1.34,
                kickoff=(now + timedelta(hours=2)).isoformat(timespec="seconds"),
            ),
            _bet_payload(
                fixture_id=11,
                probability=0.68,
                odd=1.25,
                kickoff=(now + timedelta(minutes=20)).isoformat(timespec="seconds"),
            ),
            _bet_payload(
                fixture_id=12,
                probability=0.66,
                odd=1.48,
                kickoff=(now - timedelta(minutes=15)).isoformat(timespec="seconds"),
                status_short="2H",
                status_jogo="Second Half",
            ),
            _bet_payload(
                fixture_id=13,
                probability=0.82,
                odd=1.70,
                kickoff=(now - timedelta(hours=2)).isoformat(timespec="seconds"),
                status_short="FT",
                status_jogo="Finished",
            ),
        ],
    )

    with client:
        _criar_usuario_base(
            settings.caminho_banco,
            nome="Admin 2",
            email="admin2@example.com",
            senha="segredo123",
            perfil="admin",
            plano="pro",
        )
        _login(client, email="admin2@example.com", senha="segredo123")
        response = client.get("/bets")

    assert response.status_code == 200
    payload = response.json()
    assert [bet["fixture_id"] for bet in payload["bets"]] == [10, 11, 12]
    assert payload["dashboard_perfil"] == "admin"


def test_free_user_filters_finished_started_short_window_and_low_odd(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)
    now = datetime.now()
    _salvar_payload_dashboard(
        tmp_path,
        [
            _bet_payload(
                fixture_id=21,
                probability=0.90,
                odd=1.60,
                kickoff=(now - timedelta(hours=2)).isoformat(timespec="seconds"),
                status_short="FT",
                status_jogo="Finished",
            ),
            _bet_payload(
                fixture_id=22,
                probability=0.88,
                odd=1.55,
                kickoff=(now - timedelta(minutes=10)).isoformat(timespec="seconds"),
                status_short="1H",
                status_jogo="First Half",
            ),
            _bet_payload(
                fixture_id=23,
                probability=0.86,
                odd=1.55,
                kickoff=(now + timedelta(minutes=30)).isoformat(timespec="seconds"),
            ),
            _bet_payload(
                fixture_id=24,
                probability=0.84,
                odd=1.20,
                kickoff=(now + timedelta(hours=2)).isoformat(timespec="seconds"),
            ),
            _bet_payload(
                fixture_id=25,
                probability=0.80,
                odd=1.40,
                kickoff=(now + timedelta(hours=3)).isoformat(timespec="seconds"),
            ),
        ],
    )

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Gratis", email="gratis@example.com", senha="segredo123")
        _login(client, email="gratis@example.com", senha="segredo123")
        response = client.get("/bets")

    assert response.status_code == 200
    payload = response.json()
    assert [bet["fixture_id"] for bet in payload["bets"]] == [25]


def test_free_user_without_eligible_bet_gets_upgrade_message(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)
    now = datetime.now()
    _salvar_payload_dashboard(
        tmp_path,
        [
            _bet_payload(
                fixture_id=31,
                probability=0.74,
                odd=1.25,
                kickoff=(now + timedelta(hours=2)).isoformat(timespec="seconds"),
            ),
            _bet_payload(
                fixture_id=32,
                probability=0.71,
                odd=1.55,
                kickoff=(now + timedelta(minutes=45)).isoformat(timespec="seconds"),
            ),
        ],
    )

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Gratis", email="gratis@example.com", senha="segredo123")
        _login(client, email="gratis@example.com", senha="segredo123")
        response = client.get("/bets")

    payload = response.json()
    assert payload["bets"] == []
    assert payload["dashboard_estado"] == "gratis_sem_elegivel"
    assert payload["dashboard_mostrar_upgrade"] is True
    assert payload["dashboard_mensagem"] == "Nenhuma recomendacao gratuita disponivel no momento."


def test_all_users_get_empty_state_without_upgrade_when_no_valid_bets(monkeypatch, tmp_path):
    client, settings = _build_client(monkeypatch, tmp_path)
    now = datetime.now()
    _salvar_payload_dashboard(
        tmp_path,
        [
            _bet_payload(
                fixture_id=41,
                probability=0.74,
                odd=1.40,
                kickoff=(now - timedelta(hours=1)).isoformat(timespec="seconds"),
                status_short="FT",
                status_jogo="Finished",
            ),
            _bet_payload(
                fixture_id=42,
                probability=0.71,
                odd=1.55,
                kickoff=(now - timedelta(minutes=10)).isoformat(timespec="seconds"),
                status_short="FT",
                status_jogo="Finished",
            ),
        ],
    )

    with client:
        _criar_usuario_base(settings.caminho_banco, nome="Gratis", email="gratis@example.com", senha="segredo123")
        _login(client, email="gratis@example.com", senha="segredo123")
        response = client.get("/bets")

    payload = response.json()
    assert payload["bets"] == []
    assert payload["dashboard_estado"] == "vazio_global"
    assert payload["dashboard_mostrar_upgrade"] is False
    assert payload["dashboard_mensagem"] == "Nenhuma recomendacao disponivel no momento."
