"""Servicos utilitarios para autenticacao, sessao e bootstrap de admin."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from db.repositorio_acesso import (
    DadosNovaRecuperacaoSenha,
    DadosNovaSessaoUsuario,
    DadosNovoUsuario,
    RepositorioAcessoSQLite,
)
from services.email_service import EmailService, EmailTransacional


class AutenticacaoErro(Exception):
    """Erro de validacao ou autenticacao exibido de forma amigavel ao usuario."""


@dataclass(frozen=True)
class ResultadoSessaoAutenticada:
    token: str
    expira_em: datetime


@dataclass(frozen=True)
class ResultadoRecuperacaoSenha:
    token: str
    expira_em: datetime


@dataclass(frozen=True)
class AnaliseForcaSenha:
    nivel: str
    pontuacao: int
    atende_minimos: bool
    requisitos: dict[str, bool]


class AutenticacaoService:
    """Responsavel por hash de senha, cadastro, login e sessao."""

    _SCRYPT_N = 2**14
    _SCRYPT_R = 8
    _SCRYPT_P = 1
    _SCRYPT_DKLEN = 64
    _FORMATO_HASH = "scrypt"
    _EMAIL_RE = re.compile(
        r"^(?=.{6,254}$)(?=.{1,64}@)"
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
        r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$"
    )
    _SENHAS_COMUNS_BLOQUEADAS = {
        "12345678",
        "123456789",
        "1234567890",
        "12345678901",
        "123456789012",
        "admin123",
        "password",
        "password123",
        "qwerty123",
        "senha123",
        "senhaforte123",
        "abc123456",
        "welcome123",
        "letmein123",
        "nome123456",
    }
    _PLANOS_VALIDOS = {"gratis", "pro"}
    _STATUS_VALIDOS = {"ativo", "bloqueado"}

    @staticmethod
    def normalizar_email(email: str) -> str:
        return str(email or "").strip().lower()

    @classmethod
    def validar_email(cls, email: str) -> bool:
        return bool(cls._EMAIL_RE.match(str(email or "").strip()))

    @staticmethod
    def _normalizar_texto_seguro(valor: str) -> str:
        texto = unicodedata.normalize("NFKD", str(valor or "").strip().lower())
        texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
        return texto

    @classmethod
    def _normalizar_token_senha(cls, valor: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", cls._normalizar_texto_seguro(valor))

    @classmethod
    def _parece_sequencia_simples(cls, senha: str) -> bool:
        texto = cls._normalizar_token_senha(senha)
        if not texto:
            return False
        sequencias = (
            "01234567890123456789",
            "abcdefghijklmnopqrstuvwxyz",
            "qwertyuiopasdfghjklzxcvbnm",
        )
        for tamanho in range(4, len(texto) + 1):
            trecho = texto[:tamanho]
            if any(trecho in base for base in sequencias):
                return True
        return False

    @classmethod
    def _conta_classes_caracteres(cls, senha: str) -> int:
        return sum(
            (
                bool(re.search(r"[a-z]", senha)),
                bool(re.search(r"[A-Z]", senha)),
                bool(re.search(r"\d", senha)),
                bool(re.search(r"[^A-Za-z0-9\s]", senha)),
            )
        )

    @classmethod
    def _parece_baseada_em_dados_pessoais(cls, senha: str, nome: str = "", email: str = "") -> bool:
        senha_normalizada = cls._normalizar_token_senha(senha)
        if not senha_normalizada:
            return False

        nome_normalizado = cls._normalizar_texto_seguro(nome)
        for parte in nome_normalizado.split():
            token = cls._normalizar_token_senha(parte)
            if len(token) >= 3 and token in senha_normalizada:
                return True

        email_local = cls._normalizar_token_senha(str(email or "").split("@", 1)[0])
        return len(email_local) >= 3 and email_local in senha_normalizada

    @classmethod
    def analisar_forca_senha(cls, senha: str, *, nome: str = "", email: str = "") -> AnaliseForcaSenha:
        senha_limpa = str(senha or "")
        senha_normalizada = cls._normalizar_token_senha(senha_limpa)
        tem_letra = bool(re.search(r"[A-Za-z]", senha_limpa))
        tem_numero = bool(re.search(r"\d", senha_limpa))
        tem_simbolo = bool(re.search(r"[^A-Za-z0-9\s]", senha_limpa))
        tem_reforco = cls._conta_classes_caracteres(senha_limpa) >= 3
        senha_comum = senha_normalizada in cls._SENHAS_COMUNS_BLOQUEADAS
        senha_pessoal = cls._parece_baseada_em_dados_pessoais(senha_limpa, nome=nome, email=email)
        senha_sequencial = cls._parece_sequencia_simples(senha_limpa)

        requisitos = {
            "minimo_10": len(senha_limpa) >= 10,
            "minimo_14": len(senha_limpa) >= 14,
            "tem_letra": tem_letra,
            "tem_numero_ou_simbolo": tem_numero or tem_simbolo,
            "tem_reforco": tem_reforco,
            "nao_comum": not senha_comum,
            "nao_pessoal": not senha_pessoal,
            "nao_sequencial": not senha_sequencial,
        }
        atende_minimos = (
            requisitos["minimo_10"]
            and requisitos["tem_letra"]
            and requisitos["tem_numero_ou_simbolo"]
            and requisitos["nao_comum"]
            and requisitos["nao_pessoal"]
            and requisitos["nao_sequencial"]
        )
        pontuacao = (
            int(requisitos["minimo_10"])
            + int(requisitos["minimo_14"])
            + cls._conta_classes_caracteres(senha_limpa)
            + int(requisitos["nao_comum"])
            + int(requisitos["nao_pessoal"])
            + int(requisitos["nao_sequencial"])
        )
        if not senha_limpa or not atende_minimos:
            nivel = "fraca"
        elif requisitos["minimo_14"] and cls._conta_classes_caracteres(senha_limpa) >= 3:
            nivel = "forte"
        elif pontuacao >= 6:
            nivel = "normal"
        else:
            nivel = "fraca"
        return AnaliseForcaSenha(
            nivel=nivel,
            pontuacao=pontuacao,
            atende_minimos=atende_minimos,
            requisitos=requisitos,
        )

    @classmethod
    def validar_senha_cadastro(cls, senha: str, *, nome: str = "", email: str = "") -> None:
        analise = cls.analisar_forca_senha(senha, nome=nome, email=email)
        if analise.atende_minimos:
            return
        raise AutenticacaoErro(
            "Use pelo menos 10 caracteres e evite senha comum, sequencia simples ou dados pessoais."
        )

    @staticmethod
    def hash_token_sessao(token: str) -> str:
        return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()

    @staticmethod
    def hash_token_recuperacao(token: str) -> str:
        return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()

    @classmethod
    def validar_plano(cls, plano: str) -> str:
        plano_limpo = str(plano or "").strip().lower()
        if plano_limpo not in cls._PLANOS_VALIDOS:
            raise AutenticacaoErro("Plano invalido.")
        return plano_limpo

    @classmethod
    def validar_status_usuario(cls, status: str) -> str:
        status_limpo = str(status or "").strip().lower()
        if status_limpo not in cls._STATUS_VALIDOS:
            raise AutenticacaoErro("Status invalido.")
        return status_limpo

    @staticmethod
    def _expiracao_usuario_ativa(expira_em: object) -> bool:
        valor = str(expira_em or "").strip()
        if not valor:
            return True
        try:
            return datetime.fromisoformat(valor) > datetime.now()
        except Exception:
            return False

    @classmethod
    def gerar_hash_senha(cls, senha: str) -> str:
        senha_limpa = str(senha or "")
        if not senha_limpa:
            raise ValueError("A senha inicial nao pode ser vazia.")

        salt = secrets.token_bytes(16)
        derivado = hashlib.scrypt(
            senha_limpa.encode("utf-8"),
            salt=salt,
            n=cls._SCRYPT_N,
            r=cls._SCRYPT_R,
            p=cls._SCRYPT_P,
            dklen=cls._SCRYPT_DKLEN,
        )
        salt_b64 = base64.b64encode(salt).decode("ascii")
        derivado_b64 = base64.b64encode(derivado).decode("ascii")
        return (
            f"{cls._FORMATO_HASH}${cls._SCRYPT_N}${cls._SCRYPT_R}$"
            f"{cls._SCRYPT_P}${salt_b64}${derivado_b64}"
        )

    @classmethod
    def verificar_hash_senha(cls, senha: str, senha_hash: str) -> bool:
        try:
            algoritmo, n_raw, r_raw, p_raw, salt_b64, derivado_b64 = str(senha_hash).split("$", 5)
        except ValueError:
            return False

        if algoritmo != cls._FORMATO_HASH:
            return False

        try:
            salt = base64.b64decode(salt_b64.encode("ascii"))
            derivado_esperado = base64.b64decode(derivado_b64.encode("ascii"))
            derivado_atual = hashlib.scrypt(
                str(senha or "").encode("utf-8"),
                salt=salt,
                n=int(n_raw),
                r=int(r_raw),
                p=int(p_raw),
                dklen=len(derivado_esperado),
            )
        except Exception:
            return False

        return hmac.compare_digest(derivado_atual, derivado_esperado)

    @classmethod
    def cadastrar_usuario(
        cls,
        repositorio: RepositorioAcessoSQLite,
        *,
        nome: str,
        email: str,
        senha: str,
        confirmar_senha: str,
    ) -> dict[str, Any]:
        nome_limpo = str(nome or "").strip()
        email_limpo = str(email or "").strip()
        email_normalizado = cls.normalizar_email(email_limpo)
        senha_limpa = str(senha or "")
        confirmar_limpa = str(confirmar_senha or "")

        if not nome_limpo:
            raise AutenticacaoErro("Informe seu nome.")
        if not email_limpo:
            raise AutenticacaoErro("Informe seu email.")
        if not cls.validar_email(email_limpo):
            raise AutenticacaoErro("Informe um email valido.")
        if repositorio.buscar_usuario_por_email_normalizado(email_normalizado):
            raise AutenticacaoErro("Este email ja esta cadastrado.")
        if not senha_limpa:
            raise AutenticacaoErro("Informe sua senha.")
        cls.validar_senha_cadastro(senha_limpa, nome=nome_limpo, email=email_limpo)
        if senha_limpa != confirmar_limpa:
            raise AutenticacaoErro("A confirmacao de senha nao confere.")

        usuario_id = repositorio.criar_usuario(
            DadosNovoUsuario(
                nome=nome_limpo,
                email=email_limpo,
                email_normalizado=email_normalizado,
                senha_hash=cls.gerar_hash_senha(senha_limpa),
                perfil="usuario",
                plano="gratis",
                status="ativo",
                expira_em=None,
            )
        )
        usuario = repositorio.buscar_usuario_por_id(usuario_id)
        if not usuario:
            raise RuntimeError("Falha ao recarregar o usuario criado.")
        return usuario

    @classmethod
    def autenticar_usuario(
        cls,
        repositorio: RepositorioAcessoSQLite,
        *,
        email: str,
        senha: str,
    ) -> dict[str, Any]:
        email_limpo = str(email or "").strip()
        senha_limpa = str(senha or "")
        email_normalizado = cls.normalizar_email(email_limpo)

        if not email_limpo:
            raise AutenticacaoErro("Informe seu email.")
        if not cls.validar_email(email_limpo):
            raise AutenticacaoErro("Informe um email valido.")
        if not senha_limpa:
            raise AutenticacaoErro("Informe sua senha.")

        usuario = repositorio.buscar_usuario_por_email_normalizado(email_normalizado)
        if not usuario:
            raise AutenticacaoErro("Usuario nao encontrado.")
        if str(usuario.get("status") or "") == "bloqueado":
            raise AutenticacaoErro("Seu usuario esta bloqueado.")
        if not cls._expiracao_usuario_ativa(usuario.get("expira_em")):
            raise AutenticacaoErro("Seu acesso expirou.")
        if not cls.verificar_hash_senha(senha_limpa, str(usuario.get("senha_hash") or "")):
            raise AutenticacaoErro("Senha invalida.")

        repositorio.atualizar_ultimo_login_em(int(usuario["id"]))
        usuario_atualizado = repositorio.buscar_usuario_por_id(int(usuario["id"]))
        if not usuario_atualizado:
            raise RuntimeError("Falha ao recarregar o usuario autenticado.")
        return usuario_atualizado

    @classmethod
    def criar_sessao_autenticada(
        cls,
        repositorio: RepositorioAcessoSQLite,
        *,
        usuario_id: int,
        duracao_horas: int,
        ip: str = "",
        user_agent: str = "",
    ) -> ResultadoSessaoAutenticada:
        token = secrets.token_urlsafe(32)
        expira_em = datetime.now() + timedelta(hours=max(int(duracao_horas), 1))
        repositorio.criar_sessao_usuario(
            DadosNovaSessaoUsuario(
                usuario_id=usuario_id,
                token_sessao_hash=cls.hash_token_sessao(token),
                expira_em=expira_em.isoformat(timespec="seconds"),
                ip=str(ip or ""),
                user_agent=str(user_agent or ""),
            )
        )
        return ResultadoSessaoAutenticada(token=token, expira_em=expira_em)

    @classmethod
    def obter_usuario_por_token_sessao(
        cls,
        repositorio: RepositorioAcessoSQLite,
        token_sessao: str,
    ) -> dict[str, Any] | None:
        token_limpo = str(token_sessao or "").strip()
        if not token_limpo:
            return None
        sessao = repositorio.buscar_sessao_ativa_por_token_hash(cls.hash_token_sessao(token_limpo))
        if not sessao:
            return None
        if str(sessao.get("status") or "") != "ativo":
            return None
        if not cls._expiracao_usuario_ativa(sessao.get("expira_em")):
            return None
        return sessao

    @classmethod
    def encerrar_sessao(
        cls,
        repositorio: RepositorioAcessoSQLite,
        token_sessao: str,
    ) -> int:
        token_limpo = str(token_sessao or "").strip()
        if not token_limpo:
            return 0
        return repositorio.encerrar_sessao_por_token_hash(cls.hash_token_sessao(token_limpo))

    @classmethod
    def criar_recuperacao_senha(
        cls,
        repositorio: RepositorioAcessoSQLite,
        *,
        usuario_id: int,
        duracao_minutos: int,
        ip: str = "",
        user_agent: str = "",
    ) -> ResultadoRecuperacaoSenha:
        repositorio.cancelar_recuperacoes_ativas_por_usuario_id(usuario_id)
        token = secrets.token_urlsafe(32)
        expira_em = datetime.now() + timedelta(minutes=max(int(duracao_minutos), 5))
        repositorio.criar_recuperacao_senha(
            DadosNovaRecuperacaoSenha(
                usuario_id=usuario_id,
                token_hash=cls.hash_token_recuperacao(token),
                expira_em=expira_em.isoformat(timespec="seconds"),
                ip_solicitacao=str(ip or ""),
                user_agent_solicitacao=str(user_agent or ""),
            )
        )
        return ResultadoRecuperacaoSenha(token=token, expira_em=expira_em)

    @classmethod
    def solicitar_recuperacao_senha(
        cls,
        repositorio: RepositorioAcessoSQLite,
        *,
        email: str,
        duracao_minutos: int,
        app_base_url: str,
        ip: str = "",
        user_agent: str = "",
    ) -> None:
        email_limpo = str(email or "").strip()
        if not email_limpo:
            raise AutenticacaoErro("Informe seu email.")
        if not cls.validar_email(email_limpo):
            raise AutenticacaoErro("Informe um email valido.")
        if not str(app_base_url or "").strip():
            raise AutenticacaoErro("Recuperacao de senha indisponivel no momento.")

        usuario = repositorio.buscar_usuario_por_email_normalizado(cls.normalizar_email(email_limpo))
        if not usuario:
            return

        recuperacao = cls.criar_recuperacao_senha(
            repositorio,
            usuario_id=int(usuario["id"]),
            duracao_minutos=duracao_minutos,
            ip=ip,
            user_agent=user_agent,
        )
        link = f"{str(app_base_url).rstrip('/')}/redefinir-senha?token={recuperacao.token}"
        email_transacional = EmailTransacional(
            destinatario=str(usuario.get("email") or email_limpo),
            assunto="OddsEdge | Recuperacao de senha",
            texto=(
                "Recebemos uma solicitacao para redefinir sua senha no OddsEdge.\n\n"
                f"Use este link: {link}\n\n"
                f"Este link expira em {max(int(duracao_minutos), 5)} minutos.\n"
                "Se voce nao solicitou essa alteracao, pode ignorar este email."
            ),
            html=(
                "<p>Recebemos uma solicitacao para redefinir sua senha no OddsEdge.</p>"
                f"<p><a href=\"{link}\">Clique aqui para redefinir sua senha</a></p>"
                f"<p>Este link expira em {max(int(duracao_minutos), 5)} minutos.</p>"
                "<p>Se voce nao solicitou essa alteracao, pode ignorar este email.</p>"
            ),
        )
        try:
            EmailService.enviar_email(email_transacional)
        except Exception as exc:
            repositorio.cancelar_recuperacoes_ativas_por_usuario_id(int(usuario["id"]))
            raise AutenticacaoErro("Nao foi possivel processar sua solicitacao agora.") from exc

    @classmethod
    def validar_token_recuperacao(
        cls,
        repositorio: RepositorioAcessoSQLite,
        token: str,
    ) -> dict[str, Any]:
        token_limpo = str(token or "").strip()
        if not token_limpo:
            raise AutenticacaoErro("Link de recuperacao invalido.")
        recuperacao = repositorio.buscar_recuperacao_ativa_por_token_hash(
            cls.hash_token_recuperacao(token_limpo)
        )
        if not recuperacao:
            raise AutenticacaoErro("Link de recuperacao invalido ou expirado.")
        return recuperacao

    @classmethod
    def redefinir_senha_por_token(
        cls,
        repositorio: RepositorioAcessoSQLite,
        *,
        token: str,
        senha: str,
        confirmar_senha: str,
    ) -> dict[str, Any]:
        recuperacao = cls.validar_token_recuperacao(repositorio, token)
        senha_limpa = str(senha or "")
        confirmar_limpa = str(confirmar_senha or "")

        if not senha_limpa:
            raise AutenticacaoErro("Informe sua nova senha.")
        cls.validar_senha_cadastro(
            senha_limpa,
            nome=str(recuperacao.get("nome") or ""),
            email=str(recuperacao.get("email") or ""),
        )
        if senha_limpa != confirmar_limpa:
            raise AutenticacaoErro("A confirmacao de senha nao confere.")

        usuario_id = int(recuperacao["usuario_id"])
        repositorio.atualizar_senha_usuario(usuario_id, cls.gerar_hash_senha(senha_limpa))
        repositorio.marcar_recuperacao_senha_como_utilizada(int(recuperacao["recuperacao_id"]))
        repositorio.cancelar_recuperacoes_ativas_por_usuario_id(usuario_id)
        repositorio.encerrar_sessoes_por_usuario_id(usuario_id)

        usuario_atualizado = repositorio.buscar_usuario_por_id(usuario_id)
        if not usuario_atualizado:
            raise RuntimeError("Falha ao recarregar o usuario apos redefinir a senha.")
        return usuario_atualizado

    @classmethod
    def atualizar_plano_usuario(
        cls,
        repositorio: RepositorioAcessoSQLite,
        *,
        usuario_id: int,
        plano: str,
    ) -> int:
        plano_validado = cls.validar_plano(plano)
        return repositorio.atualizar_plano_usuario(usuario_id, plano_validado)

    @classmethod
    def atualizar_status_usuario(
        cls,
        repositorio: RepositorioAcessoSQLite,
        *,
        usuario_id: int,
        status: str,
    ) -> int:
        status_validado = cls.validar_status_usuario(status)
        linhas = repositorio.atualizar_status_usuario(usuario_id, status_validado)
        if linhas and status_validado == "bloqueado":
            repositorio.encerrar_sessoes_por_usuario_id(usuario_id)
        return linhas

    @classmethod
    def garantir_admin_inicial(
        cls,
        repositorio: RepositorioAcessoSQLite,
        *,
        nome: str,
        email: str,
        senha: str,
    ) -> bool:
        if repositorio.contar_admins() > 0:
            return False

        nome_limpo = str(nome or "").strip()
        email_limpo = str(email or "").strip()
        email_normalizado = cls.normalizar_email(email_limpo)
        if not nome_limpo:
            raise ValueError("ADMIN_NOME_INICIAL precisa estar definido para criar o admin inicial.")
        if not email_limpo or not email_normalizado:
            raise ValueError("ADMIN_EMAIL_INICIAL precisa estar definido para criar o admin inicial.")

        repositorio.criar_usuario(
            DadosNovoUsuario(
                nome=nome_limpo,
                email=email_limpo,
                email_normalizado=email_normalizado,
                senha_hash=cls.gerar_hash_senha(senha),
                perfil="admin",
                plano="pro",
                status="ativo",
                expira_em=None,
            )
        )
        return True
