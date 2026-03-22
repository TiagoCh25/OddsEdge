import sqlite3
from types import SimpleNamespace

import app.bootstrap_acesso as bootstrap_module
from services.autenticacao_service import AutenticacaoService


def test_password_hash_is_generated_and_can_be_verified():
    senha = "admin123"

    senha_hash = AutenticacaoService.gerar_hash_senha(senha)

    assert senha_hash
    assert senha_hash != senha
    assert AutenticacaoService.verificar_hash_senha(senha, senha_hash) is True
    assert AutenticacaoService.verificar_hash_senha("senha-errada", senha_hash) is False


def test_bootstrap_creates_initial_admin_when_missing(monkeypatch, tmp_path):
    db_path = tmp_path / "historico_apostas.db"
    monkeypatch.setattr(
        bootstrap_module,
        "settings",
        SimpleNamespace(
            caminho_banco=db_path,
            admin_nome_inicial="Admin",
            admin_email_inicial="tiagoch25@gmail.com",
            admin_senha_inicial="admin123",
        ),
    )

    bootstrap_module.inicializar_base_acesso()

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT nome, email, email_normalizado, senha_hash, perfil, plano, status
            FROM usuarios
            WHERE perfil = 'admin'
            """
        ).fetchone()

    assert row is not None
    assert row[0] == "Admin"
    assert row[1] == "tiagoch25@gmail.com"
    assert row[2] == "tiagoch25@gmail.com"
    assert row[4] == "admin"
    assert row[5] == "pro"
    assert row[6] == "ativo"
    assert row[3] != "admin123"
    assert AutenticacaoService.verificar_hash_senha("admin123", row[3]) is True


def test_bootstrap_does_not_duplicate_admin(monkeypatch, tmp_path):
    db_path = tmp_path / "historico_apostas.db"
    monkeypatch.setattr(
        bootstrap_module,
        "settings",
        SimpleNamespace(
            caminho_banco=db_path,
            admin_nome_inicial="Admin",
            admin_email_inicial="tiagoch25@gmail.com",
            admin_senha_inicial="admin123",
        ),
    )

    bootstrap_module.inicializar_base_acesso()
    bootstrap_module.inicializar_base_acesso()

    with sqlite3.connect(db_path) as connection:
        admin_count = connection.execute(
            "SELECT COUNT(*) FROM usuarios WHERE perfil = 'admin'"
        ).fetchone()[0]

    assert admin_count == 1
