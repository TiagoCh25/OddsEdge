"""Repositorio SQLite para acesso, usuarios, planos e sessoes."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DadosNovoUsuario:
    nome: str
    email: str
    email_normalizado: str
    senha_hash: str
    perfil: str
    plano: str
    status: str
    expira_em: str | None = None


@dataclass(frozen=True)
class DadosNovaSessaoUsuario:
    usuario_id: int
    token_sessao_hash: str
    expira_em: str
    ip: str = ""
    user_agent: str = ""


@dataclass(frozen=True)
class DadosNovaRecuperacaoSenha:
    usuario_id: int
    token_hash: str
    expira_em: str
    ip_solicitacao: str = ""
    user_agent_solicitacao: str = ""


class RepositorioAcessoSQLite:
    """Persistencia de acesso no mesmo SQLite usado pelo projeto."""

    def __init__(self, caminho_banco: Path) -> None:
        self._caminho_banco = Path(caminho_banco)
        self._caminho_banco.parent.mkdir(parents=True, exist_ok=True)
        self.inicializar_estrutura()

    def _conexao(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._caminho_banco), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def inicializar_estrutura(self) -> None:
        with self._conexao() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL,
                    email_normalizado TEXT NOT NULL,
                    senha_hash TEXT NOT NULL,
                    perfil TEXT NOT NULL CHECK (perfil IN ('usuario', 'admin')),
                    plano TEXT NOT NULL CHECK (plano IN ('gratis', 'pro')),
                    status TEXT NOT NULL CHECK (status IN ('ativo', 'bloqueado')),
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    ultimo_login_em TEXT,
                    expira_em TEXT
                );

                CREATE TABLE IF NOT EXISTS planos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    limite_apostas_dia INTEGER,
                    preco_mensal_centavos INTEGER NOT NULL DEFAULT 0,
                    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessoes_usuario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    token_sessao_hash TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    expira_em TEXT NOT NULL,
                    encerrada_em TEXT,
                    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                    ip TEXT,
                    user_agent TEXT,
                    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
                );

                CREATE TABLE IF NOT EXISTS recuperacoes_senha (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    expira_em TEXT NOT NULL,
                    utilizado_em TEXT,
                    cancelado_em TEXT,
                    ip_solicitacao TEXT,
                    user_agent_solicitacao TEXT,
                    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email_normalizado ON usuarios(email_normalizado);
                CREATE INDEX IF NOT EXISTS idx_usuarios_perfil ON usuarios(perfil);
                CREATE INDEX IF NOT EXISTS idx_usuarios_plano ON usuarios(plano);
                CREATE INDEX IF NOT EXISTS idx_usuarios_status ON usuarios(status);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_planos_codigo ON planos(codigo);
                CREATE INDEX IF NOT EXISTS idx_planos_ativo ON planos(ativo);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_sessoes_usuario_token_sessao_hash
                    ON sessoes_usuario(token_sessao_hash);
                CREATE INDEX IF NOT EXISTS idx_sessoes_usuario_usuario_id ON sessoes_usuario(usuario_id);
                CREATE INDEX IF NOT EXISTS idx_sessoes_usuario_expira_em ON sessoes_usuario(expira_em);
                CREATE INDEX IF NOT EXISTS idx_sessoes_usuario_ativo ON sessoes_usuario(ativo);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_recuperacoes_senha_token_hash
                    ON recuperacoes_senha(token_hash);
                CREATE INDEX IF NOT EXISTS idx_recuperacoes_senha_usuario_id
                    ON recuperacoes_senha(usuario_id);
                CREATE INDEX IF NOT EXISTS idx_recuperacoes_senha_expira_em
                    ON recuperacoes_senha(expira_em);
                """
            )
            self._inserir_planos_iniciais(conn)

    def _inserir_planos_iniciais(self, conn: sqlite3.Connection) -> None:
        agora = self._agora()
        planos = (
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
        )
        for plano in planos:
            conn.execute(
                """
                INSERT INTO planos (
                    codigo,
                    nome,
                    descricao,
                    limite_apostas_dia,
                    preco_mensal_centavos,
                    ativo,
                    criado_em,
                    atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(codigo) DO UPDATE SET
                    nome = excluded.nome,
                    descricao = excluded.descricao,
                    limite_apostas_dia = excluded.limite_apostas_dia,
                    preco_mensal_centavos = excluded.preco_mensal_centavos,
                    ativo = excluded.ativo,
                    atualizado_em = excluded.atualizado_em
                """,
                (
                    plano["codigo"],
                    plano["nome"],
                    plano["descricao"],
                    plano["limite_apostas_dia"],
                    plano["preco_mensal_centavos"],
                    plano["ativo"],
                    agora,
                    agora,
                ),
            )

    @staticmethod
    def _agora() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def contar_admins(self) -> int:
        with self._conexao() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM usuarios WHERE perfil = 'admin'"
            ).fetchone()
        return int(row["total"]) if row else 0

    def criar_usuario(self, dados: DadosNovoUsuario) -> int:
        agora = self._agora()
        with self._conexao() as conn:
            cursor = conn.execute(
                """
                INSERT INTO usuarios (
                    nome,
                    email,
                    email_normalizado,
                    senha_hash,
                    perfil,
                    plano,
                    status,
                    criado_em,
                    atualizado_em,
                    ultimo_login_em,
                    expira_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dados.nome,
                    dados.email,
                    dados.email_normalizado,
                    dados.senha_hash,
                    dados.perfil,
                    dados.plano,
                    dados.status,
                    agora,
                    agora,
                    None,
                    dados.expira_em,
                ),
            )
        return int(cursor.lastrowid)

    def buscar_usuario_por_id(self, usuario_id: int) -> dict[str, Any] | None:
        with self._conexao() as conn:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE id = ?",
                (usuario_id,),
            ).fetchone()
        return dict(row) if row else None

    def buscar_usuario_por_email_normalizado(self, email_normalizado: str) -> dict[str, Any] | None:
        with self._conexao() as conn:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE email_normalizado = ?",
                (email_normalizado,),
            ).fetchone()
        return dict(row) if row else None

    def atualizar_ultimo_login_em(self, usuario_id: int) -> None:
        agora = self._agora()
        with self._conexao() as conn:
            conn.execute(
                """
                UPDATE usuarios
                SET ultimo_login_em = ?, atualizado_em = ?
                WHERE id = ?
                """,
                (agora, agora, usuario_id),
            )

    def criar_sessao_usuario(self, dados: DadosNovaSessaoUsuario) -> int:
        agora = self._agora()
        with self._conexao() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessoes_usuario (
                    usuario_id,
                    token_sessao_hash,
                    criado_em,
                    atualizado_em,
                    expira_em,
                    encerrada_em,
                    ativo,
                    ip,
                    user_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dados.usuario_id,
                    dados.token_sessao_hash,
                    agora,
                    agora,
                    dados.expira_em,
                    None,
                    1,
                    dados.ip,
                    dados.user_agent,
                ),
            )
        return int(cursor.lastrowid)

    def buscar_sessao_ativa_por_token_hash(self, token_sessao_hash: str) -> dict[str, Any] | None:
        agora = self._agora()
        with self._conexao() as conn:
            row = conn.execute(
                """
                SELECT
                    s.id AS sessao_id,
                    s.usuario_id,
                    s.token_sessao_hash,
                    s.criado_em AS sessao_criado_em,
                    s.atualizado_em AS sessao_atualizado_em,
                    s.expira_em AS sessao_expira_em,
                    s.encerrada_em,
                    s.ativo AS sessao_ativa,
                    s.ip,
                    s.user_agent,
                    u.id,
                    u.nome,
                    u.email,
                    u.email_normalizado,
                    u.senha_hash,
                    u.perfil,
                    u.plano,
                    u.status,
                    u.criado_em,
                    u.atualizado_em,
                    u.ultimo_login_em,
                    u.expira_em
                FROM sessoes_usuario s
                INNER JOIN usuarios u ON u.id = s.usuario_id
                WHERE
                    s.token_sessao_hash = ?
                    AND s.ativo = 1
                    AND s.encerrada_em IS NULL
                    AND s.expira_em > ?
                LIMIT 1
                """,
                (token_sessao_hash, agora),
            ).fetchone()
        return dict(row) if row else None

    def encerrar_sessao_por_token_hash(self, token_sessao_hash: str) -> int:
        agora = self._agora()
        with self._conexao() as conn:
            cursor = conn.execute(
                """
                UPDATE sessoes_usuario
                SET ativo = 0, encerrada_em = ?, atualizado_em = ?
                WHERE token_sessao_hash = ? AND ativo = 1
                """,
                (agora, agora, token_sessao_hash),
            )
        return int(cursor.rowcount or 0)

    def encerrar_sessoes_por_usuario_id(self, usuario_id: int) -> int:
        agora = self._agora()
        with self._conexao() as conn:
            cursor = conn.execute(
                """
                UPDATE sessoes_usuario
                SET ativo = 0, encerrada_em = ?, atualizado_em = ?
                WHERE usuario_id = ? AND ativo = 1
                """,
                (agora, agora, usuario_id),
            )
        return int(cursor.rowcount or 0)

    def cancelar_recuperacoes_ativas_por_usuario_id(self, usuario_id: int) -> int:
        agora = self._agora()
        with self._conexao() as conn:
            cursor = conn.execute(
                """
                UPDATE recuperacoes_senha
                SET cancelado_em = ?, atualizado_em = ?
                WHERE
                    usuario_id = ?
                    AND utilizado_em IS NULL
                    AND cancelado_em IS NULL
                    AND expira_em > ?
                """,
                (agora, agora, usuario_id, agora),
            )
        return int(cursor.rowcount or 0)

    def criar_recuperacao_senha(self, dados: DadosNovaRecuperacaoSenha) -> int:
        agora = self._agora()
        with self._conexao() as conn:
            cursor = conn.execute(
                """
                INSERT INTO recuperacoes_senha (
                    usuario_id,
                    token_hash,
                    criado_em,
                    atualizado_em,
                    expira_em,
                    utilizado_em,
                    cancelado_em,
                    ip_solicitacao,
                    user_agent_solicitacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dados.usuario_id,
                    dados.token_hash,
                    agora,
                    agora,
                    dados.expira_em,
                    None,
                    None,
                    dados.ip_solicitacao,
                    dados.user_agent_solicitacao,
                ),
            )
        return int(cursor.lastrowid)

    def buscar_recuperacao_ativa_por_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        agora = self._agora()
        with self._conexao() as conn:
            row = conn.execute(
                """
                SELECT
                    r.id AS recuperacao_id,
                    r.usuario_id,
                    r.token_hash,
                    r.criado_em AS recuperacao_criado_em,
                    r.atualizado_em AS recuperacao_atualizado_em,
                    r.expira_em AS recuperacao_expira_em,
                    r.utilizado_em,
                    r.cancelado_em,
                    r.ip_solicitacao,
                    r.user_agent_solicitacao,
                    u.id,
                    u.nome,
                    u.email,
                    u.email_normalizado,
                    u.senha_hash,
                    u.perfil,
                    u.plano,
                    u.status,
                    u.criado_em,
                    u.atualizado_em,
                    u.ultimo_login_em,
                    u.expira_em
                FROM recuperacoes_senha r
                INNER JOIN usuarios u ON u.id = r.usuario_id
                WHERE
                    r.token_hash = ?
                    AND r.utilizado_em IS NULL
                    AND r.cancelado_em IS NULL
                    AND r.expira_em > ?
                LIMIT 1
                """,
                (token_hash, agora),
            ).fetchone()
        return dict(row) if row else None

    def marcar_recuperacao_senha_como_utilizada(self, recuperacao_id: int) -> int:
        agora = self._agora()
        with self._conexao() as conn:
            cursor = conn.execute(
                """
                UPDATE recuperacoes_senha
                SET utilizado_em = ?, atualizado_em = ?
                WHERE id = ? AND utilizado_em IS NULL
                """,
                (agora, agora, recuperacao_id),
            )
        return int(cursor.rowcount or 0)

    def atualizar_senha_usuario(self, usuario_id: int, senha_hash: str) -> int:
        agora = self._agora()
        with self._conexao() as conn:
            cursor = conn.execute(
                """
                UPDATE usuarios
                SET senha_hash = ?, atualizado_em = ?
                WHERE id = ?
                """,
                (senha_hash, agora, usuario_id),
            )
        return int(cursor.rowcount or 0)

    def obter_resumo_usuarios(self) -> dict[str, int]:
        with self._conexao() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_usuarios,
                    SUM(CASE WHEN perfil = 'admin' THEN 1 ELSE 0 END) AS total_admins,
                    SUM(CASE WHEN plano = 'gratis' THEN 1 ELSE 0 END) AS total_plano_gratis,
                    SUM(CASE WHEN plano = 'pro' THEN 1 ELSE 0 END) AS total_plano_pro
                FROM usuarios
                """
            ).fetchone()
        if not row:
            return {
                "total_usuarios": 0,
                "total_admins": 0,
                "total_plano_gratis": 0,
                "total_plano_pro": 0,
            }
        return {
            "total_usuarios": int(row["total_usuarios"] or 0),
            "total_admins": int(row["total_admins"] or 0),
            "total_plano_gratis": int(row["total_plano_gratis"] or 0),
            "total_plano_pro": int(row["total_plano_pro"] or 0),
        }

    def listar_usuarios(self) -> list[dict[str, Any]]:
        with self._conexao() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    nome,
                    email,
                    perfil,
                    plano,
                    status,
                    criado_em
                FROM usuarios
                ORDER BY id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def atualizar_plano_usuario(self, usuario_id: int, plano: str) -> int:
        agora = self._agora()
        with self._conexao() as conn:
            cursor = conn.execute(
                """
                UPDATE usuarios
                SET plano = ?, atualizado_em = ?
                WHERE id = ?
                """,
                (plano, agora, usuario_id),
            )
        return int(cursor.rowcount or 0)

    def atualizar_status_usuario(self, usuario_id: int, status: str) -> int:
        agora = self._agora()
        with self._conexao() as conn:
            cursor = conn.execute(
                """
                UPDATE usuarios
                SET status = ?, atualizado_em = ?
                WHERE id = ?
                """,
                (status, agora, usuario_id),
            )
        return int(cursor.rowcount or 0)

    def listar_planos(self) -> list[dict[str, Any]]:
        with self._conexao() as conn:
            rows = conn.execute(
                """
                SELECT
                    codigo,
                    nome,
                    descricao,
                    limite_apostas_dia,
                    preco_mensal_centavos,
                    ativo
                FROM planos
                ORDER BY id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]
