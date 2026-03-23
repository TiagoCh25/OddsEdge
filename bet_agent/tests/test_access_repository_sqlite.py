import sqlite3

import pytest

from db.repositorio_acesso import DadosNovoUsuario, RepositorioAcessoSQLite
from services.autenticacao_service import AutenticacaoService


def test_access_repository_initialization_is_idempotent(tmp_path):
    db_path = tmp_path / "historico_apostas.db"

    repository = RepositorioAcessoSQLite(db_path)
    repository.inicializar_estrutura()
    RepositorioAcessoSQLite(db_path)

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        plans_count = connection.execute("SELECT COUNT(*) FROM planos").fetchone()[0]

    assert {"usuarios", "planos", "sessoes_usuario"}.issubset(tables)
    assert plans_count == 2


def test_initial_plans_are_seeded_idempotently(tmp_path):
    db_path = tmp_path / "historico_apostas.db"
    repository = RepositorioAcessoSQLite(db_path)

    repository.inicializar_estrutura()
    plans = repository.listar_planos()

    assert plans == [
        {
            "codigo": "gratis",
            "nome": "Grátis",
            "descricao": "1 recomendação por dia",
            "limite_apostas_dia": 1,
            "preco_mensal_centavos": 0,
            "ativo": 1,
        },
        {
            "codigo": "pro",
            "nome": "Pro",
            "descricao": "acesso completo às recomendações",
            "limite_apostas_dia": None,
            "preco_mensal_centavos": 0,
            "ativo": 1,
        },
    ]


def test_email_and_email_normalizado_must_be_unique(tmp_path):
    db_path = tmp_path / "historico_apostas.db"
    repository = RepositorioAcessoSQLite(db_path)
    senha_hash = AutenticacaoService.gerar_hash_senha("segredo123")

    repository.criar_usuario(
        DadosNovoUsuario(
            nome="Tiago",
            email="tiago@example.com",
            email_normalizado="tiago@example.com",
            senha_hash=senha_hash,
            perfil="usuario",
            plano="gratis",
            status="ativo",
        )
    )

    with pytest.raises(sqlite3.IntegrityError):
        repository.criar_usuario(
            DadosNovoUsuario(
                nome="Outro",
                email="tiago@example.com",
                email_normalizado="outro@example.com",
                senha_hash=senha_hash,
                perfil="usuario",
                plano="gratis",
                status="ativo",
            )
        )

    with pytest.raises(sqlite3.IntegrityError):
        repository.criar_usuario(
            DadosNovoUsuario(
                nome="Outro",
                email="Tiago@Example.com",
                email_normalizado="tiago@example.com",
                senha_hash=senha_hash,
                perfil="usuario",
                plano="gratis",
                status="ativo",
            )
        )
